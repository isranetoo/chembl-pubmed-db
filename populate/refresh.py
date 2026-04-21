"""
refresh.py
----------
Atualiza as views materializadas após um novo populate.

Uso:
    python refresh.py                  # atualiza as 3 views
    python refresh.py --view profile   # atualiza só mv_compound_profile
    python refresh.py --view articles  # atualiza só mv_compound_articles
    python refresh.py --view full      # atualiza só mv_compound_full
    python refresh.py --status         # mostra quando cada view foi atualizada pela última vez
"""

import argparse
import logging
import sys

import psycopg2
import psycopg2.extras

from config import DB_CONFIG

log = logging.getLogger(__name__)

# Mapeamento alias → nome real da view
VIEWS = {
    "profile":  "mv_compound_profile",
    "articles": "mv_compound_articles",
    "full":     "mv_compound_full",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="refresh.py",
        description="Atualiza as views materializadas do banco ChEMBL+PubMed.",
    )
    parser.add_argument(
        "--view",
        choices=list(VIEWS.keys()),
        default=None,
        help="Atualiza apenas uma view específica. Sem esta flag, atualiza todas.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Mostra quando cada view foi atualizada pela última vez e quantas linhas tem.",
    )
    return parser.parse_args()


def show_status(cur) -> None:
    """Exibe linhas e horário de refresh de cada view materializada."""
    log.info("Status das views materializadas:")
    log.info("-" * 50)

    for alias, view_name in VIEWS.items():
        try:
            cur.execute(f"SELECT COUNT(*), MAX(refreshed_at) FROM {view_name}")
            row = cur.fetchone()
            count       = row[0] if row else 0
            last_update = row[1].strftime("%Y-%m-%d %H:%M") if row and row[1] else "nunca"
            log.info(f"  {view_name:<30} {count:>6} linhas  | atualizada: {last_update}")
        except Exception as exc:
            log.warning(f"  {view_name}: erro — {exc}")

    log.info("-" * 50)


def refresh_view(cur, view_name: str) -> float:
    """
    Executa REFRESH MATERIALIZED VIEW CONCURRENTLY e retorna duração em ms.
    CONCURRENTLY permite leituras simultâneas durante o refresh.
    """
    cur.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}")
    return 0.0


def refresh_all_via_function(cur) -> None:
    """Usa a função SQL refresh_materialized_views() para atualizar tudo."""
    cur.execute("SELECT view_name, duration_ms FROM refresh_materialized_views()")
    rows = cur.fetchall()
    for view_name, duration_ms in rows:
        log.info(f"  {view_name:<30} atualizada em {duration_ms:.0f} ms")


def main() -> None:
    args = parse_args()

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True   # REFRESH MATERIALIZED VIEW não pode rodar dentro de transação
    cur  = conn.cursor()

    if args.status:
        show_status(cur)
        cur.close()
        conn.close()
        return

    if args.view:
        # Atualizar view específica
        view_name = VIEWS[args.view]
        log.info(f"Atualizando {view_name}...")
        try:
            import time
            t0 = time.perf_counter()
            refresh_view(cur, view_name)
            elapsed = (time.perf_counter() - t0) * 1000
            log.info(f"  {view_name} atualizada em {elapsed:.0f} ms.")
        except Exception as exc:
            log.error(f"Erro ao atualizar {view_name}: {exc}")
            sys.exit(1)
    else:
        # Atualizar tudo via função SQL
        log.info("Atualizando todas as views materializadas...")
        try:
            refresh_all_via_function(cur)
            log.info("Concluido.")
        except Exception as exc:
            log.error(f"Erro ao chamar refresh_materialized_views(): {exc}")
            log.info("Tentando atualizar individualmente...")
            import time
            for alias, view_name in VIEWS.items():
                try:
                    t0 = time.perf_counter()
                    refresh_view(cur, view_name)
                    elapsed = (time.perf_counter() - t0) * 1000
                    log.info(f"  {view_name} atualizada em {elapsed:.0f} ms.")
                except Exception as e:
                    log.error(f"  {view_name}: {e}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()