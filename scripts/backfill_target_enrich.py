"""
backfill_target_enrich.py
-------------------------
Preenche, para alvos JÁ existentes no banco, os campos enriquecidos
introduzidos pela migration 0006_target_enrich:

  - targets.tax_id, species_group_flag
  - target_components (accession UniProt, gene_symbol, type, …)
  - target_xrefs (PDB, GO, Reactome, InterPro, Pfam, HGNC, …)

Por que existe
--------------
Targets gravados antes da migration 0006 têm tax_id NULL e nenhuma linha
em target_components/xrefs. populate.py recém-modificado já faz esse
enrichment quando processa compostos (etapa 8), mas este script é útil
para:

  - re-rodar SÓ o enrichment, sem o overhead do pipeline completo
  - processar lotes (filtros por --limit, --only)
  - testar com --dry-run antes de tocar o banco

Como rodar
----------
Pré-requisito: migration 0006 já aplicada (alembic upgrade head).

    python scripts/backfill_target_enrich.py
    python scripts/backfill_target_enrich.py --only CHEMBL1862
    python scripts/backfill_target_enrich.py --limit 20 --dry-run

Idempotente: rodar duas vezes não duplica nem regride dados.
"""

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2

from populate.chembl_client import fetch_target
from populate.config import DB_CONFIG
from populate.db import upsert_target, upsert_target_components


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


SLEEP_BETWEEN = 0.2  # gentileza com a API


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="backfill_target_enrich.py",
        description="Preenche tax_id + components + xrefs em targets sem enrichment.",
    )
    p.add_argument(
        "--only", metavar="CHEMBL_ID", action="append", default=[],
        help="Processa só estes target IDs (pode repetir).",
    )
    p.add_argument(
        "--limit", type=int, default=None,
        help="Limita o número de targets processados (útil pra testar).",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Não escreve no banco; só loga o que faria.",
    )
    return p.parse_args()


def list_targets_to_enrich(cur, only: list[str], limit: int | None) -> list[str]:
    """Retorna chembl_id dos targets com tax_id NULL (precisam enrich)."""
    if only:
        cur.execute(
            "SELECT chembl_id FROM targets WHERE chembl_id = ANY(%s) AND tax_id IS NULL ORDER BY chembl_id",
            ([cid.upper() for cid in only],),
        )
    else:
        sql = "SELECT chembl_id FROM targets WHERE tax_id IS NULL ORDER BY created_at, chembl_id"
        if limit:
            sql += f" LIMIT {int(limit)}"
        cur.execute(sql)
    return [r[0] for r in cur.fetchall()]


def main() -> None:
    args = parse_args()

    log.info("Conectando ao banco %s/%s...", DB_CONFIG.get("host"), DB_CONFIG.get("dbname"))
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur  = conn.cursor()

    chembl_ids = list_targets_to_enrich(cur, args.only, args.limit)
    log.info("Targets sem enrichment: %d", len(chembl_ids))
    if args.dry_run:
        log.info("[DRY-RUN] Nenhuma escrita será feita.")

    stats = {"ok": 0, "sem_dado": 0, "erro": 0, "components_total": 0}

    for i, chembl_id in enumerate(chembl_ids, 1):
        log.info("[%d/%d] %s", i, len(chembl_ids), chembl_id)
        try:
            data = fetch_target(chembl_id)
            if not data:
                log.warning("  Sem retorno da API — pulando.")
                stats["sem_dado"] += 1
                continue

            components = data.get("components") or []
            n_xrefs    = sum(len(c.get("xrefs") or []) for c in components)
            genes      = [c.get("gene_symbol") for c in components if c.get("gene_symbol")]

            if args.dry_run:
                log.info(
                    "  [DRY] tax_id=%s | components=%d | xrefs=%d | genes=%s",
                    data.get("tax_id"), len(components), n_xrefs, ", ".join(genes) or "?",
                )
                stats["ok"] += 1
                continue

            target_id = upsert_target(cur, data)
            n_comp = upsert_target_components(cur, target_id, components)
            stats["components_total"] += n_comp

            conn.commit()
            log.info(
                "  tax_id=%s | components=+%d | xrefs=%d | genes=%s",
                data.get("tax_id"), n_comp, n_xrefs, ", ".join(genes) or "?",
            )
            stats["ok"] += 1
            time.sleep(SLEEP_BETWEEN)

        except Exception as exc:
            log.error("  Erro em %s: %s", chembl_id, exc)
            conn.rollback()
            stats["erro"] += 1

    cur.close()
    conn.close()

    log.info("=" * 55)
    log.info(
        "Concluído — ok: %d | sem retorno: %d | erros: %d | components total: %d",
        stats["ok"], stats["sem_dado"], stats["erro"], stats["components_total"],
    )


if __name__ == "__main__":
    main()
