"""
backfill_bioactivity_enrich.py
------------------------------
Re-popula bioatividades de compostos que têm linhas legadas (sem
assay_type/activity_id) — herdadas de execuções anteriores à migration
0005_bioactivity_enrich.

Estratégia:
  1. Listar compostos com EXISTS (bioactivities WHERE assay_type IS NULL)
  2. Para cada um: delete_legacy_bioactivities + fetch + upsert
  3. Targets são re-resolvidos via upsert_target (idempotente).

Não toca em compostos cujas bioatividades já estão enriquecidas.

Como rodar
----------
Pré-requisito: migration 0005 já aplicada (alembic upgrade head).

    python scripts/backfill_bioactivity_enrich.py
    python scripts/backfill_bioactivity_enrich.py --only CHEMBL941
    python scripts/backfill_bioactivity_enrich.py --limit 5 --dry-run

Idempotente: rodar duas vezes não duplica nem regride dados.
"""

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2

from populate.chembl_client import (
    fetch_bioactivities,
    fetch_target,
    normalize_bioactivity,
)
from populate.config import DB_CONFIG
from populate.db import (
    delete_legacy_bioactivities,
    upsert_bioactivity,
    upsert_target,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


SLEEP_BETWEEN_TARGETS = 0.2  # gentileza com a API
SLEEP_BETWEEN_COMPS   = 0.5


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="backfill_bioactivity_enrich.py",
        description="Re-popula bioatividades legadas com pchembl, assay, journal, LE, etc.",
    )
    p.add_argument(
        "--only", metavar="CHEMBL_ID", action="append", default=[],
        help="Processa só estes IDs (pode repetir). Sem isto, processa todos os legados.",
    )
    p.add_argument(
        "--limit", type=int, default=None,
        help="Limita o número de compostos processados (útil pra testar).",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Não escreve no banco; só conta o que faria.",
    )
    return p.parse_args()


def list_legacy_compounds(cur, only: list[str], limit: int | None) -> list[tuple[str, str]]:
    """
    Retorna (compound_uuid, chembl_id) dos compostos com bioatividades legadas.
    Critério: tem ≥ 1 linha em bioactivities com assay_type IS NULL.
    """
    if only:
        cur.execute(
            """
            SELECT c.id::text, c.chembl_id
            FROM compounds c
            WHERE c.chembl_id = ANY(%s)
              AND EXISTS (
                  SELECT 1 FROM bioactivities b
                  WHERE b.compound_id = c.id
                    AND b.assay_type  IS NULL
              )
            ORDER BY c.chembl_id
            """,
            ([cid.upper() for cid in only],),
        )
    else:
        sql = """
            SELECT c.id::text, c.chembl_id
            FROM compounds c
            WHERE EXISTS (
                SELECT 1 FROM bioactivities b
                WHERE b.compound_id = c.id
                  AND b.assay_type  IS NULL
            )
            ORDER BY c.created_at, c.chembl_id
        """
        if limit:
            sql += f" LIMIT {int(limit)}"
        cur.execute(sql)
    return cur.fetchall()


def process_one(cur, compound_uuid: str, chembl_id: str, dry_run: bool) -> dict:
    """Re-fetch + upsert bioatividades de UM composto. Retorna contadores."""
    stats = {"deleted": 0, "inserted": 0, "skipped": 0}

    if dry_run:
        cur.execute(
            "SELECT COUNT(*) FROM bioactivities WHERE compound_id = %s AND assay_type IS NULL",
            (compound_uuid,),
        )
        stats["deleted"] = cur.fetchone()[0]
        activities = fetch_bioactivities(chembl_id)
        stats["inserted"] = len([a for a in activities if a.get("target_chembl_id")])
        return stats

    stats["deleted"] = delete_legacy_bioactivities(cur, compound_uuid)

    activities = fetch_bioactivities(chembl_id)
    target_cache: dict[str, str] = {}

    for raw_act in activities:
        t_chembl = raw_act.get("target_chembl_id")
        if not t_chembl:
            stats["skipped"] += 1
            continue
        if t_chembl not in target_cache:
            target = fetch_target(t_chembl)
            if not target:
                stats["skipped"] += 1
                time.sleep(SLEEP_BETWEEN_TARGETS)
                continue
            target_cache[t_chembl] = upsert_target(cur, target)
            time.sleep(SLEEP_BETWEEN_TARGETS)
        target_id = target_cache[t_chembl]

        act = normalize_bioactivity(raw_act)
        upsert_bioactivity(cur, compound_uuid, target_id, act)
        stats["inserted"] += 1

    return stats


def main() -> None:
    args = parse_args()

    log.info("Conectando ao banco %s/%s...", DB_CONFIG.get("host"), DB_CONFIG.get("dbname"))
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur  = conn.cursor()

    rows = list_legacy_compounds(cur, args.only, args.limit)
    log.info("Compostos com bioatividades legadas: %d", len(rows))
    if args.dry_run:
        log.info("[DRY-RUN] Nenhuma escrita será feita.")

    totals = {"ok": 0, "erro": 0, "deleted": 0, "inserted": 0}

    for i, (compound_uuid, chembl_id) in enumerate(rows, 1):
        log.info("[%d/%d] %s", i, len(rows), chembl_id)
        try:
            stats = process_one(cur, compound_uuid, chembl_id, args.dry_run)
            if not args.dry_run:
                conn.commit()
            log.info(
                "  legadas removidas: %d | inseridas/atualizadas: %d | sem target: %d",
                stats["deleted"], stats["inserted"], stats.get("skipped", 0),
            )
            totals["ok"] += 1
            totals["deleted"]  += stats["deleted"]
            totals["inserted"] += stats["inserted"]
            time.sleep(SLEEP_BETWEEN_COMPS)
        except Exception as exc:
            log.error("  Erro em %s: %s", chembl_id, exc)
            conn.rollback()
            totals["erro"] += 1

    cur.close()
    conn.close()

    log.info("=" * 55)
    log.info(
        "Concluído — ok: %d | erros: %d | total legadas removidas: %d | "
        "total bioatividades enriquecidas: %d",
        totals["ok"], totals["erro"], totals["deleted"], totals["inserted"],
    )


if __name__ == "__main__":
    main()
