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
) -> Iterator[tuple[str, str]]:
    """
    Itera CHEMBL{start_id}..CHEMBL{end_id} (inclusivo nos dois lados).
    Yields (chembl_id, pref_name) apenas para moleculas com `pref_name` nao vazio.

    404 e tratado como "nao existe nesse ID" — apenas pula sem warning.
    Erros de rede sao logados como warning e continuam para o proximo ID.
    """
    if start_id > end_id:
        raise ValueError("start_id nao pode ser maior que end_id")

    session = _create_session()
    try:
        for n in range(start_id, end_id + 1):
            cid = f"CHEMBL{n}"
            url = f"{CHEMBL_MOLECULE_URL}/{cid}.json"

            try:
                r = session.get(url, timeout=REQUEST_TIMEOUT)
            except requests.RequestException as exc:
                log.warning(f"  {cid}: erro de rede ({exc})")
                continue

            if r.status_code == 404:
                continue
            if not r.ok:
                log.warning(f"  {cid}: HTTP {r.status_code}")
                continue

            try:
                mol = r.json()
            except ValueError:
                log.warning(f"  {cid}: resposta nao-JSON")
                continue

            chembl_id = (mol.get("molecule_chembl_id") or "").strip()
            pref_name = (mol.get("pref_name") or "").strip()
            if chembl_id and pref_name:
                yield chembl_id, pref_name

            time.sleep(sleep_seconds)
    finally:
        session.close()


def upsert_seed_compounds(
    rows: list[tuple[str, str]],
    category: str = "Outros",
) -> dict:
    """
    Upsert na tabela `seed_compounds`. Idempotente: ON CONFLICT DO NOTHING
    nao sobrescreve `common_name`/`category` de linhas existentes (preserva
    edicoes manuais e a categorizacao mais especifica do seed inicial).

    Retorna {"inserted": int, "kept": int, "total": int}.
    """
    if not rows:
        return {"inserted": 0, "kept": 0, "total": 0}

    inserted = 0
    with psycopg2.connect(**DB_CONFIG) as conn:
        cur = conn.cursor()
        for cid, name in rows:
            cur.execute(
                """
                INSERT INTO seed_compounds (chembl_id, common_name, category)
                VALUES (%s, %s, %s)
                ON CONFLICT (chembl_id) DO NOTHING
                """,
                (cid, name, category),
            )
            inserted += cur.rowcount
        conn.commit()
        cur.close()

    return {
        "inserted": inserted,
        "kept":     len(rows) - inserted,
        "total":    len(rows),
    }


def scrape_and_seed(
    start_id:      int,
    end_id:        int,
    category:      str = "Outros",
    export_csv:    Optional[str] = None,
    sleep_seconds: float = 0.05,
) -> dict:
    """
    Orquestra scrape + upsert. Retorna stats agregadas.
    Esta e a funcao chamada pelo scheduler na etapa 0 do pipeline.
    """
    log.info(f"Scrape ChEMBL: {start_id}..{end_id} (categoria default: {category!r})")
    rows = list(iter_named_molecules(start_id, end_id, sleep_seconds))
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
        f"{stats['kept']} ja existiam | {stats['total']} total"
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
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    scrape_and_seed(
        start_id      = args.start,
        end_id        = args.end,
        category      = args.category,
        export_csv    = args.export_csv,
        sleep_seconds = args.sleep,
    )


if __name__ == "__main__":
    main()
