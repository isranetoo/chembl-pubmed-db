"""
scraper.py
----------
Varre o ChEMBL por faixa de IDs e popula a tabela `seed_compounds`.

Substitui o projeto standalone `scraper-chembl-pubmed/` — a saida vai direto
para o banco local em vez de gerar CSV/listas Python (use `--export-csv` se
ainda quiser o artefato).

Uso programatico (chamado pelo scheduler):
    from populate.scraper import scrape_and_seed
    stats = scrape_and_seed(start_id=10000, end_id=15000)

CLI:
    python -m populate.scraper --start 10000 --end 15000
    python -m populate.scraper --start 10000 --end 15000 --export-csv out.csv

Estrategia:
    - Para cada N em [start..end], consulta /molecule/CHEMBL{N}.json.
    - Nome resolvido por prioridade: pref_name → molecule_synonyms[0] → chembl_id.
    - Categoria resolvida por prioridade: indication_class → ATC nivel 1 → "Outros".
    - Upsert em `seed_compounds`: insere novos e atualiza `category` de existentes.
      `common_name` e `is_active` nunca sao sobrescritos (preserva edicoes manuais).

Depois do scrape, basta rodar `populate.py` normalmente: ele vai pegar os
novos chembl_ids automaticamente via `load_popular_compounds()` e buscar
ADMET/bioativ./mecanismos/PubMed.
"""

from __future__ import annotations

import argparse
import csv
import logging
import time
from typing import Iterator, Optional

import psycopg2
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import CHEMBL_BASE, DB_CONFIG

log = logging.getLogger(__name__)

CHEMBL_MOLECULE_URL = f"{CHEMBL_BASE}/molecule"
REQUEST_TIMEOUT = (10, 20)


def _create_session() -> requests.Session:
    """
    Sessao com retry para 429/5xx, igual ao scraper original.
    Nao usa `populate.http_retry.get_with_retry` porque aquela funcao retenta
    em 4xx — para o scraper, 404 e o caso esperado (faixa esparsa de IDs).
    """
    retry = Retry(
        total=3, connect=3, read=3, status=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    s = requests.Session()
    s.headers.update({"Accept": "application/json"})
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


_ATC_CATEGORY: dict[str, str] = {
    "A": "Trato Alimentar e Metabolismo",
    "B": "Sangue e Órgãos Hematopoéticos",
    "C": "Cardiovascular",
    "D": "Dermatológicos",
    "G": "Geniturinário e Hormônios Sexuais",
    "H": "Hormônios Sistêmicos",
    "J": "Anti-infecciosos",
    "L": "Oncologia",
    "M": "Musculoesquelético",
    "N": "Sistema Nervoso",
    "P": "Antiparasitários",
    "R": "Respiratório",
    "S": "Órgãos dos Sentidos",
    "V": "Vários",
}


def _resolve_name(mol: dict, chembl_id: str) -> tuple[str, str]:
    """
    Retorna (nome, fonte) para um mol ChEMBL.
    Prioridade: pref_name → primeiro synonym → chembl_id.
    """
    pref_name = (mol.get("pref_name") or "").strip()
    if pref_name:
        return pref_name, "pref_name"

    syns = mol.get("molecule_synonyms") or []
    if syns:
        syn = (syns[0].get("molecule_synonym") or "").strip()
        if syn:
            return syn, "synonym"

    return chembl_id, "id_fallback"


def _resolve_category(mol: dict) -> str:
    """
    Retorna a categoria terapeutica do composto.
    Prioridade: indication_class → ATC nivel 1 → "Outros".
    """
    indication = (mol.get("indication_class") or "").strip()
    if indication:
        return indication

    atc_list = mol.get("atc_classifications") or []
    if atc_list:
        letter = atc_list[0][0].upper() if atc_list[0] else ""
        if letter in _ATC_CATEGORY:
            return _ATC_CATEGORY[letter]

    return "Outros"


def iter_named_molecules(
    start_id: int,
    end_id: int,
    sleep_seconds: float = 0.05,
    progress_every: int = 25,
) -> Iterator[tuple[str, str, str]]:
    """
    Itera CHEMBL{start_id}..CHEMBL{end_id} (inclusivo nos dois lados).
    Yields (chembl_id, nome, categoria) para todas as moleculas que existem.

    Nome resolvido em ordem: pref_name → molecule_synonyms[0] → chembl_id.
    Categoria resolvida em ordem: indication_class → ATC nivel 1 → "Outros".
    404 e tratado como "nao existe nesse ID" — apenas pula sem warning.
    Erros de rede sao logados como warning e continuam para o proximo ID.

    A cada `progress_every` IDs processados, emite um log de progresso com
    contagens parciais, taxa (IDs/s) e ETA. Use progress_every<=0 para silenciar.
    """
    if start_id > end_id:
        raise ValueError("start_id nao pode ser maior que end_id")

    total        = end_id - start_id + 1
    processed    = 0
    found        = 0
    not_found    = 0
    via_syn      = 0
    via_id_only  = 0
    errors       = 0
    t_start      = time.monotonic()

    session = _create_session()
    try:
        for n in range(start_id, end_id + 1):
            cid = f"CHEMBL{n}"
            url = f"{CHEMBL_MOLECULE_URL}/{cid}.json"

            try:
                r = session.get(url, timeout=REQUEST_TIMEOUT)
            except requests.RequestException as exc:
                log.warning(f"  {cid}: erro de rede ({exc})")
                errors    += 1
                processed += 1
                continue

            if r.status_code == 404:
                not_found += 1
            elif not r.ok:
                log.warning(f"  {cid}: HTTP {r.status_code}")
                errors += 1
            else:
                try:
                    mol = r.json()
                    chembl_id = (mol.get("molecule_chembl_id") or "").strip()
                    if chembl_id:
                        name, source = _resolve_name(mol, chembl_id)
                        category     = _resolve_category(mol)
                        found += 1
                        if source == "synonym":
                            via_syn += 1
                        elif source == "id_fallback":
                            via_id_only += 1
                        log.debug(f"  + {chembl_id}: {name!r} [{source}] | {category}")
                        yield chembl_id, name, category
                    else:
                        not_found += 1
                except ValueError:
                    log.warning(f"  {cid}: resposta nao-JSON")
                    errors += 1

            processed += 1

            if progress_every > 0 and processed % progress_every == 0:
                elapsed = time.monotonic() - t_start
                rate    = processed / elapsed if elapsed > 0 else 0.0
                remain  = total - processed
                eta_s   = remain / rate if rate > 0 else 0.0
                pct     = 100.0 * processed / total
                log.info(
                    f"  progresso: {processed}/{total} ({pct:5.1f}%) | "
                    f"encontrados={found} (syn={via_syn}, id_fb={via_id_only}) | "
                    f"404={not_found} | erros={errors} | "
                    f"{rate:.1f} IDs/s | ETA ~{eta_s:5.0f}s"
                )

            time.sleep(sleep_seconds)
    finally:
        session.close()
        elapsed = time.monotonic() - t_start
        log.info(
            f"  fim do scrape: {processed}/{total} IDs em {elapsed:.1f}s "
            f"| encontrados={found} (syn={via_syn}, id_fb={via_id_only}) "
            f"| 404={not_found} | erros={errors}"
        )


def upsert_seed_compounds(
    rows: list[tuple[str, str, str]],
) -> dict:
    """
    Upsert na tabela `seed_compounds`.

    - Novos compostos: inseridos com nome e categoria da API.
    - Compostos existentes: apenas `category` e atualizada (categoria vem da API).
      `common_name` e `is_active` nunca sao sobrescritos (preserva edicoes manuais).

    Apos o upsert, faz um SELECT confirmatorio para garantir que todos os
    chembl_ids do lote estao realmente persistidos no banco.

    Retorna {"inserted": int, "updated": int, "total": int, "verified": int,
    "missing": list[str]}.
    """
    if not rows:
        return {"inserted": 0, "updated": 0, "total": 0, "verified": 0, "missing": []}

    all_ids        = [cid for cid, *_ in rows]
    inserted_ids:  list[str] = []
    updated_ids:   list[str] = []
    changed_cats:  list[tuple[str, str, str]] = []  # (chembl_id, old_cat, new_cat)

    with psycopg2.connect(**DB_CONFIG) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS seed_compounds (
                chembl_id    TEXT PRIMARY KEY,
                common_name  TEXT NOT NULL,
                category     TEXT,
                is_active    BOOLEAN NOT NULL DEFAULT TRUE,
                added_at     TIMESTAMP DEFAULT NOW()
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_seed_compounds_active "
            "ON seed_compounds(is_active)"
        )

        # Captura categorias atuais antes do upsert para detectar mudancas.
        cur.execute(
            "SELECT chembl_id, category FROM seed_compounds WHERE chembl_id = ANY(%s)",
            (all_ids,),
        )
        old_categories: dict[str, str | None] = {r[0]: r[1] for r in cur.fetchall()}

        new_cat_by_id = {cid: cat for cid, _, cat in rows}

        for cid, name, cat in rows:
            cur.execute(
                """
                INSERT INTO seed_compounds (chembl_id, common_name, category)
                VALUES (%s, %s, %s)
                ON CONFLICT (chembl_id) DO UPDATE
                    SET category = EXCLUDED.category
                RETURNING chembl_id, (xmax = 0) AS is_new
                """,
                (cid, name, cat),
            )
            row = cur.fetchone()
            if row is not None:
                if row[1]:
                    inserted_ids.append(row[0])
                else:
                    updated_ids.append(row[0])
                    old_cat = old_categories.get(cid)
                    new_cat = new_cat_by_id[cid]
                    if old_cat != new_cat:
                        changed_cats.append((cid, old_cat or "None", new_cat))
        conn.commit()

        # Verificacao: todos os IDs do lote precisam existir no banco agora.
        cur.execute(
            "SELECT chembl_id FROM seed_compounds WHERE chembl_id = ANY(%s)",
            (all_ids,),
        )
        present = {r[0] for r in cur.fetchall()}
        cur.close()

    missing  = [cid for cid in all_ids if cid not in present]
    inserted = len(inserted_ids)
    updated  = len(updated_ids)

    log.info(f"  novos inseridos ({inserted}): {inserted_ids}")
    if changed_cats:
        for cid, old_cat, new_cat in changed_cats:
            log.info(f"  categoria alterada: {cid} | {old_cat!r} → {new_cat!r}")
    else:
        log.info(f"  categoria atualizada ({updated}): sem mudancas nos existentes")
    if missing:
        log.error(f"  FALTANDO no banco ({len(missing)}): {missing}")
    else:
        log.info(f"  verificacao OK: {len(present)}/{len(all_ids)} chembl_ids presentes em seed_compounds")

    return {
        "inserted": inserted,
        "updated":  updated,
        "total":    len(rows),
        "verified": len(present),
        "missing":  missing,
    }


def scrape_and_seed(
    start_id:       int,
    end_id:         int,
    export_csv:     Optional[str] = None,
    sleep_seconds:  float = 0.05,
    progress_every: int = 25,
    batch_size:     int = 50,
) -> dict:
    """
    Orquestra scrape + upsert em lotes. Retorna stats agregadas.
    Esta e a funcao chamada pelo scheduler na etapa 0 do pipeline.

    Insere no banco a cada `batch_size` compostos encontrados — se o processo
    cair no meio, os lotes ja commitados estao salvos.
    A categoria e resolvida automaticamente pela API (indication_class → ATC → "Outros").
    """
    log.info(f"Scrape ChEMBL: {start_id}..{end_id} (lote={batch_size}, categoria=da API)")

    csv_file:   Optional[object] = None
    csv_writer: Optional[object] = None
    if export_csv:
        csv_file   = open(export_csv, "w", newline="", encoding="utf-8")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["chembl_id", "pref_name", "category"])

    agg = {"inserted": 0, "updated": 0, "total": 0, "verified": 0, "missing": []}
    buffer: list[tuple[str, str, str]] = []
    scraped = 0

    def _flush(buf: list[tuple[str, str, str]]) -> None:
        stats = upsert_seed_compounds(buf)
        agg["inserted"] += stats["inserted"]
        agg["updated"]  += stats["updated"]
        agg["total"]    += stats["total"]
        agg["verified"] += stats["verified"]
        agg["missing"].extend(stats["missing"])

    try:
        for chembl_id, name, category in iter_named_molecules(
            start_id, end_id, sleep_seconds, progress_every=progress_every,
        ):
            scraped += 1
            buffer.append((chembl_id, name, category))

            if csv_writer:
                csv_writer.writerow([chembl_id, name, category])
                csv_file.flush()

            if len(buffer) >= batch_size:
                log.info(f"  [lote] {len(buffer)} compostos → banco")
                _flush(buffer)
                buffer = []

        if buffer:
            log.info(f"  [lote final] {len(buffer)} compostos → banco")
            _flush(buffer)

    finally:
        if csv_file:
            csv_file.close()
            if export_csv:
                log.info(f"  CSV exportado: {export_csv}")

    log.info(
        f"  seed_compounds: {agg['inserted']} novos | "
        f"{agg['updated']} categoria atualizada | {agg['total']} total | "
        f"verificados no banco: {agg['verified']}/{agg['total']}"
    )
    return {"scraped": scraped, **agg}


# ============================================================
# CLI
# ============================================================

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="populate.scraper",
        description="Varre faixa de CHEMBL IDs e popula seed_compounds.",
    )
    p.add_argument("--start",    type=int, required=True, help="Primeiro CHEMBL N (incl.)")
    p.add_argument("--end",      type=int, required=True, help="Ultimo CHEMBL N (incl.)")
    p.add_argument("--export-csv", metavar="FILE", default=None,
                   help="Tambem salvar resultado em CSV (compat com scraper antigo).")
    p.add_argument("--sleep", type=float, default=0.05,
                   help="Pausa entre requisicoes em segundos (default: 0.05).")
    p.add_argument("--progress-every", type=int, default=25,
                   help="Emite log de progresso a cada N IDs (0 = silencia). Default: 25.")
    p.add_argument("--batch-size", type=int, default=50,
                   help="Insere no banco a cada N compostos encontrados (default: 50).")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    scrape_and_seed(
        start_id       = args.start,
        end_id         = args.end,
        export_csv     = args.export_csv,
        sleep_seconds  = args.sleep,
        progress_every = args.progress_every,
        batch_size     = args.batch_size,
    )


if __name__ == "__main__":
    main()