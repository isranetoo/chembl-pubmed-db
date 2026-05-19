"""
populate_clinical_trials.py
---------------------------
Popula a camada Clinical Status pra todos (ou um subset) dos compostos
do banco, chamando a CT.gov v2 via populate.clinicaltrials_client.

Uso:
    # Todos os compostos (com nome definido)
    python scripts/populate_clinical_trials.py

    # Um único composto
    python scripts/populate_clinical_trials.py --only CHEMBL941

    # Primeiros N compostos (teste rápido)
    python scripts/populate_clinical_trials.py --limit 5

    # Pular compostos que já têm trials cacheados (retomada após falha)
    python scripts/populate_clinical_trials.py --skip-synced

    # Retomar a partir de um chembl_id específico
    python scripts/populate_clinical_trials.py --start-from CHEMBL2000

    # Pausa entre compostos pra ser educado com a CT.gov
    python scripts/populate_clinical_trials.py --sleep 1.0

    # Forçar drug_name (override do compounds.name) — só faz sentido com --only
    python scripts/populate_clinical_trials.py --only CHEMBL941 --drug-name imatinib
"""

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

from populate.clinicaltrials_client import sync_compound_trials
from populate.db import get_conn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("populate_clinical_trials")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="populate_clinical_trials.py",
        description="Popula ensaios clínicos (CT.gov v2) pra compostos do banco.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--only", metavar="CHEMBL_ID",
                        help="Processar apenas este composto.")
    parser.add_argument("--drug-name", metavar="NAME",
                        help="Override do nome usado na busca (só com --only).")
    parser.add_argument("--limit", type=int, metavar="N",
                        help="Limita a quantidade de compostos processados.")
    parser.add_argument("--start-from", metavar="CHEMBL_ID",
                        help="Começa a partir deste chembl_id (ordem alfabética).")
    parser.add_argument("--skip-synced", action="store_true",
                        help="Pula compostos que já têm pelo menos 1 link em "
                             "compound_clinical_trials. Útil pra retomar.")
    parser.add_argument("--sleep", type=float, default=0.5, metavar="SEC",
                        help="Pausa entre compostos (default 0.5s).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Só lista o que seria processado, não chama a CT.gov.")
    return parser.parse_args()


def select_compounds(cur, args) -> list[tuple[str, str]]:
    """Retorna lista de (chembl_id, name) a processar conforme os filtros."""
    if args.only:
        cur.execute(
            "SELECT chembl_id, name FROM compounds WHERE chembl_id = %s",
            (args.only.upper(),),
        )
        rows = cur.fetchall()
        if not rows:
            log.error("Composto %s não encontrado.", args.only)
            sys.exit(1)
        # --drug-name só vale junto com --only; aplicamos aqui mesmo
        if args.drug_name:
            return [(rows[0][0], args.drug_name)]
        return rows

    where = ["name IS NOT NULL", "TRIM(name) <> ''"]
    params: list = []

    if args.start_from:
        where.append("chembl_id >= %s")
        params.append(args.start_from.upper())

    if args.skip_synced:
        where.append(
            "NOT EXISTS (SELECT 1 FROM compound_clinical_trials cct "
            "WHERE cct.chembl_id = compounds.chembl_id)"
        )

    sql = (
        "SELECT chembl_id, name FROM compounds WHERE "
        + " AND ".join(where)
        + " ORDER BY chembl_id"
    )
    if args.limit:
        sql += f" LIMIT {int(args.limit)}"

    cur.execute(sql, params)
    return cur.fetchall()


def main() -> None:
    args = parse_args()

    conn = get_conn()
    cur = conn.cursor()
    compounds = select_compounds(cur, args)
    cur.close()

    total = len(compounds)
    if total == 0:
        log.info("Nenhum composto pra processar.")
        conn.close()
        return

    log.info("=" * 60)
    log.info("Bulk populate de Clinical Trials")
    log.info("=" * 60)
    log.info("Compostos selecionados : %d", total)
    log.info("Pausa entre compostos  : %.1fs", args.sleep)
    if args.dry_run:
        log.info("MODO DRY-RUN — não chamará a CT.gov")
    log.info("")

    stats = {"processed": 0, "errors": 0, "trials": 0, "links": 0, "empty": 0}
    t0 = time.perf_counter()

    for i, (chembl_id, name) in enumerate(compounds, 1):
        prefix = f"[{i:>4}/{total}] {chembl_id:<14}"

        if args.dry_run:
            log.info("%s %s", prefix, name)
            continue

        # Cada composto roda em sua própria transação. Erro em um não
        # contamina o estado dos próximos.
        cur = conn.cursor()
        try:
            result = sync_compound_trials(cur, chembl_id, name)
            conn.commit()

            stats["processed"] += 1
            stats["trials"]    += result["trials_upserted"]
            stats["links"]     += result["links_created"]
            if result["links_created"] == 0:
                stats["empty"] += 1

            log.info(
                "%s fetched=%d upserted=%d links=%d  (%s)",
                prefix, result["trials_fetched"], result["trials_upserted"],
                result["links_created"], name,
            )
        except requests.RequestException as exc:
            conn.rollback()
            stats["errors"] += 1
            log.warning("%s ERRO HTTP — %s", prefix, exc)
        except Exception as exc:
            conn.rollback()
            stats["errors"] += 1
            log.warning("%s ERRO — %s", prefix, exc)
        finally:
            cur.close()

        if i < total:
            time.sleep(args.sleep)

    conn.close()
    elapsed = round(time.perf_counter() - t0, 1)

    log.info("")
    log.info("=" * 60)
    log.info("CONCLUÍDO em %ss", elapsed)
    log.info("  Compostos processados : %d", stats["processed"])
    log.info("  Sem trials (0 links)  : %d", stats["empty"])
    log.info("  Erros                 : %d", stats["errors"])
    log.info("  Trials upserted total : %d", stats["trials"])
    log.info("  Links criados total   : %d", stats["links"])
    log.info("=" * 60)


if __name__ == "__main__":
    main()
