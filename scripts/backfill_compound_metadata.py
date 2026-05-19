"""
backfill_compound_metadata.py
-----------------------------
Preenche, para compostos JÁ existentes no banco, os campos clínicos/regulatórios
e as tabelas auxiliares (synonyms, ATC) introduzidos pela migration
0004_compound_metadata.

Por que existe
--------------
populate.py só chama upsert_compound quando o composto é novo. Compostos
inseridos antes da migration 0004 ficam com NULL nos novos campos
(max_phase, first_approval, oral/parenteral/topical, withdrawn_*,
usan_*, etc.) e sem linhas em compound_synonyms / compound_atc.

Este script percorre todos os compostos e atualiza só esses dados, sem
mexer em ADMET, bioatividades, indicações, mecanismos ou artigos.

Como rodar
----------
Pré-requisito: migration 0004 já aplicada (alembic upgrade head).

    python scripts/backfill_compound_metadata.py
    python scripts/backfill_compound_metadata.py --only CHEMBL941
    python scripts/backfill_compound_metadata.py --limit 20

Idempotente: o upsert usa COALESCE/GREATEST, e as tabelas auxiliares têm
UNIQUE com ON CONFLICT — rodar duas vezes não duplica e não regride.
"""

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2

from populate.chembl_client import fetch_compound
from populate.config import DB_CONFIG
from populate.db import (
    upsert_compound,
    upsert_compound_atc,
    upsert_compound_synonyms,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


SLEEP_BETWEEN = 0.25  # gentileza com a API do ChEMBL


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="backfill_compound_metadata.py",
        description="Preenche campos clínicos/regulatórios em compostos existentes.",
    )
    p.add_argument(
        "--only", metavar="CHEMBL_ID", action="append", default=[],
        help="Processa só estes IDs (pode repetir). Sem isto, processa todos.",
    )
    p.add_argument(
        "--limit", type=int, default=None,
        help="Limita o número de compostos processados (útil pra testar).",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Não escreve no banco; só loga o que faria.",
    )
    return p.parse_args()


def list_compound_ids(cur, only: list[str], limit: int | None) -> list[str]:
    """Retorna ChEMBL IDs a processar — em ordem de inserção pra log estável."""
    if only:
        cur.execute(
            "SELECT chembl_id FROM compounds WHERE chembl_id = ANY(%s) ORDER BY chembl_id",
            ([cid.upper() for cid in only],),
        )
    else:
        sql = "SELECT chembl_id FROM compounds ORDER BY created_at, chembl_id"
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

    chembl_ids = list_compound_ids(cur, args.only, args.limit)
    log.info("Compostos a processar: %d", len(chembl_ids))
    if args.dry_run:
        log.info("[DRY-RUN] Nenhuma escrita será feita.")

    stats = {"ok": 0, "sem_dado": 0, "erro": 0, "syn_total": 0, "atc_total": 0}

    for i, chembl_id in enumerate(chembl_ids, 1):
        log.info("[%d/%d] %s", i, len(chembl_ids), chembl_id)
        try:
            data = fetch_compound(chembl_id)
            if not data:
                log.warning("  Sem retorno da API — pulando.")
                stats["sem_dado"] += 1
                continue

            n_syn = len(data.get("synonyms") or [])
            n_atc = len(data.get("atc")      or [])
            phase = data.get("max_phase")
            approval = data.get("first_approval")

            if args.dry_run:
                log.info(
                    "  [DRY] phase=%s approval=%s synonyms=%d atc=%d "
                    "oral=%s withdrawn=%s blackbox=%s usan=%s",
                    phase, approval, n_syn, n_atc,
                    data.get("oral"), data.get("withdrawn_flag"),
                    data.get("black_box_warning"), data.get("usan_stem"),
                )
                stats["ok"] += 1
                continue

            compound_id = upsert_compound(cur, data)
            stats["syn_total"] += upsert_compound_synonyms(cur, compound_id, data.get("synonyms") or [])
            stats["atc_total"] += upsert_compound_atc     (cur, compound_id, data.get("atc")      or [])

            conn.commit()
            log.info(
                "  phase=%s approval=%s | synonyms=+%d | atc=+%d | "
                "oral=%s blackbox=%s withdrawn=%s class=%s",
                phase, approval, n_syn, n_atc,
                data.get("oral"), data.get("black_box_warning"),
                data.get("withdrawn_flag"), data.get("usan_stem_definition"),
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
        "Concluído — ok: %d | sem retorno: %d | erros: %d | "
        "synonyms inseridos: %d | ATC inseridos: %d",
        stats["ok"], stats["sem_dado"], stats["erro"],
        stats["syn_total"], stats["atc_total"],
    )


if __name__ == "__main__":
    main()
