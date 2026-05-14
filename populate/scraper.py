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
    - Mantem so registros com `pref_name` nao vazio.
    - Upsert em `seed_compounds` com ON CONFLICT DO NOTHING — nao sobrescreve
      `common_name`/`category` editados manualmente nem regressao da flag
      `is_active`.

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


def iter_named_molecules(
    start_id: int,
    end_id: int,
    sleep_seconds: float = 0.05,
    progress_every: int = 25,
) -> Iterator[tuple[str, str]]:
    """
    Itera CHEMBL{start_id}..CHEMBL{end_id} (inclusivo nos dois lados).
    Yields (chembl_id, pref_name) apenas para moleculas com `pref_name` nao vazio.

    404 e tratado como "nao existe nesse ID" — apenas pula sem warning.
    Erros de rede sao logados como warning e continuam para o proximo ID.

    A cada `progress_every` IDs processados, emite um log de progresso com
    contagens parciais, taxa (IDs/s) e ETA. Use progress_every<=0 para silenciar.
    """
    if start_id > end_id:
        raise ValueError("start_id nao pode ser maior que end_id")

    total      = end_id - start_id + 1
    processed  = 0
    found      = 0
    not_found  = 0
    errors     = 0
    t_start    = time.monotonic()

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
                    pref_name = (mol.get("pref_name") or "").strip()
                    if chembl_id and pref_name:
                        found += 1
                        log.debug(f"  + {chembl_id}: {pref_name}")
                        yield chembl_id, pref_name
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
                    f"com_nome={found} | 404/sem_nome={not_found} | erros={errors} | "
                    f"{rate:.1f} IDs/s | ETA ~{eta_s:5.0f}s"
                )

            time.sleep(sleep_seconds)
    finally:
        session.close()
        elapsed = time.monotonic() - t_start
        log.info(
            f"  fim do scrape: {processed}/{total} IDs em {elapsed:.1f}s "
            f"| com_nome={found} | 404/sem_nome={not_found} | erros={errors}"
        )


def upsert_seed_compounds(
    rows: list[tuple[str, str]],
    category: str = "Outros",
) -> dict:
    """
    Upsert na tabela `seed_compounds`. Idempotente: ON CONFLICT DO NOTHING
    nao sobrescreve `common_name`/`category` de linhas existentes (preserva
    edicoes manuais e a categorizacao mais especifica do seed inicial).

    Apos o upsert, faz um SELECT confirmatorio para garantir que todos os
    chembl_ids do lote estao realmente persistidos no banco.

    Retorna {"inserted": int, "kept": int, "total": int, "verified": int,
    "missing": list[str]}.
    """
    if not rows:
        return {"inserted": 0, "kept": 0, "total": 0, "verified": 0, "missing": []}

    all_ids       = [cid for cid, _ in rows]
    inserted_ids: list[str] = []

    with psycopg2.connect(**DB_CONFIG) as conn:
        cur = conn.cursor()
        for cid, name in rows:
            cur.execute(
                """
                INSERT INTO seed_compounds (chembl_id, common_name, category)
                VALUES (%s, %s, %s)
                ON CONFLICT (chembl_id) DO NOTHING
                RETURNING chembl_id
                """,
                (cid, name, category),
            )
            row = cur.fetchone()
            if row is not None:
                inserted_ids.append(row[0])
        conn.commit()

        # Verificacao: todos os IDs do lote precisam existir no banco agora.
        cur.execute(
            "SELECT chembl_id FROM seed_compounds WHERE chembl_id = ANY(%s)",
            (all_ids,),
        )
        present = {r[0] for r in cur.fetchall()}
        cur.close()

    missing = [cid for cid in all_ids if cid not in present]
    inserted = len(inserted_ids)

    log.info(f"  novos inseridos no banco ({inserted}): {inserted_ids}")
    if missing:
        log.error(f"  FALTANDO no banco ({len(missing)}): {missing}")
    else:
        log.info(f"  verificacao OK: {len(present)}/{len(all_ids)} chembl_ids presentes em seed_compounds")

    return {
        "inserted": inserted,
        "kept":     len(rows) - inserted,
        "total":    len(rows),
        "verified": len(present),
        "missing":  missing,
    }


def scrape_and_seed(
    start_id:       int,
    end_id:         int,
    category:       str = "Outros",
    export_csv:     Optional[str] = None,
    sleep_seconds:  float = 0.05,
    progress_every: int = 25,
) -> dict:
    """
    Orquestra scrape + upsert. Retorna stats agregadas.
    Esta e a funcao chamada pelo scheduler na etapa 0 do pipeline.
    """
    log.info(f"Scrape ChEMBL: {start_id}..{end_id} (categoria default: {category!r})")
    rows = list(iter_named_molecules(
        start_id, end_id, sleep_seconds, progress_every=progress_every,
    ))
    log.info(f"  Encontrados {len(rows)} compostos com pref_name")

    if export_csv:
        with open(export_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["chembl_id", "pref_name"])
            w.writerows(rows)
        log.info(f"  CSV exportado: {export_csv}")

    stats = upsert_seed_compounds(rows, category=category)
    log.info(
        f"  seed_compounds: {stats['inserted']} novos | "
        f"{stats['kept']} ja existiam | {stats['total']} total | "
        f"verificados no banco: {stats['verified']}/{stats['total']}"
    )
    return {"scraped": len(rows), **stats}


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
    p.add_argument("--category", default="Outros",
                   help="Categoria para os novos seeds (default: 'Outros').")
    p.add_argument("--export-csv", metavar="FILE", default=None,
                   help="Tambem salvar resultado em CSV (compat com scraper antigo).")
    p.add_argument("--sleep", type=float, default=0.05,
                   help="Pausa entre requisicoes em segundos (default: 0.05).")
    p.add_argument("--progress-every", type=int, default=25,
                   help="Emite log de progresso a cada N IDs (0 = silencia). Default: 25.")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    scrape_and_seed(
        start_id       = args.start,
        end_id         = args.end,
        category       = args.category,
        export_csv     = args.export_csv,
        sleep_seconds  = args.sleep,
        progress_every = args.progress_every,
    )


if __name__ == "__main__":
    main()