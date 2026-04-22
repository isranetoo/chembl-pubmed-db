"""
migrate_to_supabase.py
----------------------
Migra todos os dados do banco local para o Supabase (ou qualquer
PostgreSQL remoto), mantendo UUIDs, FKs e constraints intactos.

Uso:
    # Definir destino via DATABASE_URL
    $env:DATABASE_URL = "postgresql://postgres.xxx:senha@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"
    python migrate_to_supabase.py

    # Ou via flags diretos
    python migrate_to_supabase.py --target-url "postgresql://..."

    # Dry-run (só conta linhas, não migra nada)
    python migrate_to_supabase.py --dry-run

    # Pular criação do schema (banco destino já tem as tabelas)
    python migrate_to_supabase.py --skip-schema

    # Migrar só algumas tabelas
    python migrate_to_supabase.py --only compounds --only articles

Estratégia:
    1. Conecta ao banco LOCAL (DB_CONFIG do config.py / .env)
    2. Conecta ao banco DESTINO (DATABASE_URL ou --target-url)
    3. Aplica todos os arquivos init/*.sql no destino (schema)
    4. Copia cada tabela em lotes (BATCH_SIZE linhas por vez)
       — respeitando a ordem de dependência das FKs
    5. Desativa triggers durante a cópia e os reativa ao final
    6. Reconstrói os tsvectors (FTS) via UPDATE
    7. Faz REFRESH das views materializadas
    8. Imprime resumo com contagens e tempo por tabela
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import psycopg2
import psycopg2.extras

# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ============================================================
# Configuração
# ============================================================

BATCH_SIZE = 500   # linhas por INSERT batch

# Ordem de migração respeita dependências de FK
TABLE_ORDER = [
    "compounds",           # sem deps
    "targets",             # sem deps
    "articles",            # sem deps
    "bioactivities",       # → compounds, targets
    "article_compounds",   # → articles, compounds
    "indications",         # → compounds
    "mechanisms",          # → compounds, targets
    "admet_properties",    # → compounds
]

# Arquivos de schema em ordem de aplicação
SCHEMA_FILES = [
    "init/01_schema.sql",
    "init/02_article_enrich.sql",
    "init/03_indications.sql",
    "init/04_mechanisms.sql",
    "init/05_admet.sql",
    "init/06_fts.sql",
    "init/07_materialized_views.sql",
]

def _find_project_root() -> Path:
    """
    Encontra a raiz do projeto buscando a pasta init/ a partir do script.
    Funciona independente do diretório de trabalho atual.
    """
    # Começa no diretório do script e sobe até encontrar init/
    candidate = Path(__file__).parent.resolve()
    for _ in range(4):   # busca até 4 níveis acima
        if (candidate / "init").is_dir():
            return candidate
        candidate = candidate.parent
    # Fallback: diretório do script mesmo que init/ não exista
    return Path(__file__).parent.resolve()


ROOT = _find_project_root()


# ============================================================
# Helpers de conexão
# ============================================================

def _parse_url(url: str) -> dict:
    p = urlparse(url)
    cfg = {
        "host":     p.hostname,
        "port":     p.port or 5432,
        "dbname":   p.path.lstrip("/"),
        "user":     p.username,
        "password": p.password,
    }
    if p.query:
        for part in p.query.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                cfg[k] = v
    if "supabase" in (p.hostname or ""):
        cfg.setdefault("sslmode", "require")
    return cfg


def connect_local() -> psycopg2.extensions.connection:
    """
    Conecta ao banco LOCAL.

    Usa variáveis individuais DB_HOST/DB_PORT/... ou os defaults do Docker.
    Ignora DATABASE_URL intencionalmente — ela aponta para o destino.
    """
    cfg = {
        "host":     os.environ.get("DB_HOST",     "localhost"),
        "port":     int(os.environ.get("DB_PORT", "5432")),
        "dbname":   os.environ.get("DB_NAME",     "chembl_pubmed"),
        "user":     os.environ.get("DB_USER",     "admin"),
        "password": os.environ.get("DB_PASSWORD", "admin123"),
    }
    if os.environ.get("DB_SSLMODE"):
        cfg["sslmode"] = os.environ["DB_SSLMODE"]

    log.info(f"Local → {cfg['host']}:{cfg['port']}/{cfg['dbname']}")
    return psycopg2.connect(**cfg)


def connect_target(url: str) -> psycopg2.extensions.connection:
    cfg = _parse_url(url)
    log.info(f"Destino → {cfg['host']}:{cfg['port']}/{cfg['dbname']}")
    return psycopg2.connect(**cfg)


# ============================================================
# Schema
# ============================================================

def apply_schema(conn_dst: psycopg2.extensions.connection) -> None:
    """Aplica todos os arquivos init/*.sql no banco destino."""
    log.info(f"Aplicando schema no destino (init/ em: {ROOT / 'init'})...")
    cur = conn_dst.cursor()

    for rel_path in SCHEMA_FILES:
        sql_file = ROOT / rel_path
        if not sql_file.exists():
            log.warning(f"  Arquivo não encontrado: {rel_path} — pulando.")
            continue

        sql = sql_file.read_text(encoding="utf-8")
        try:
            cur.execute(sql)
            conn_dst.commit()
            log.info(f"  ✓ {rel_path}")
        except Exception as exc:
            conn_dst.rollback()
            log.warning(f"  ! {rel_path}: {exc}")
            # Continuar — pode ser que as tabelas já existam

    cur.close()


# ============================================================
# Contagem de linhas
# ============================================================

def count_rows(conn, table: str) -> int:
    """Conta linhas de uma tabela. Usa ROLLBACK antes para limpar qualquer transação abortada."""
    try:
        conn.rollback()   # limpa estado de erro de queries anteriores
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        n = cur.fetchone()[0]
        cur.close()
        conn.commit()
        return n
    except Exception:
        conn.rollback()
        raise


# ============================================================
# Migração por tabela
# ============================================================

def get_columns(conn_src: psycopg2.extensions.connection, table: str) -> list[str]:
    """Retorna lista de colunas da tabela, excluindo tsvectors (são reconstruídos)."""
    cur = conn_src.cursor()
    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = %s
        ORDER BY ordinal_position
    """, (table,))
    cols = [
        row[0] for row in cur.fetchall()
        if row[1] != "tsvector"    # fts é reconstruído via trigger/UPDATE
    ]
    cur.close()
    return cols


def migrate_table(
    conn_src: psycopg2.extensions.connection,
    conn_dst: psycopg2.extensions.connection,
    table:    str,
    dry_run:  bool = False,
) -> dict:
    """
    Copia uma tabela do banco local para o destino em lotes.
    Retorna estatísticas: {rows_src, rows_dst, inserted, skipped, duration_s}
    """
    t0        = time.perf_counter()
    rows_src  = count_rows(conn_src, table)
    cols      = get_columns(conn_src, table)
    col_list  = ", ".join(f'"{c}"' for c in cols)
    placeholders = ", ".join(["%s"] * len(cols))

    # ON CONFLICT DO NOTHING — idempotente: re-execuções não duplicam
    insert_sql = (
        f'INSERT INTO {table} ({col_list}) VALUES ({placeholders}) '
        f'ON CONFLICT DO NOTHING'
    )

    log.info(f"  {table}: {rows_src} linhas | {len(cols)} colunas")

    if dry_run:
        return {
            "rows_src": rows_src, "rows_dst": count_rows(conn_dst, table),
            "inserted": 0, "skipped": 0, "duration_s": 0,
        }

    cur_src = conn_src.cursor("migration_cursor", cursor_factory=psycopg2.extras.DictCursor)
    cur_dst = conn_dst.cursor()

    # Desativar só triggers de USUÁRIO (fts, etc.)
    # DISABLE TRIGGER ALL é bloqueado no Supabase (sistema não permite
    # desativar triggers de sistema como RI_ConstraintTrigger)
    cur_dst.execute(f"ALTER TABLE {table} DISABLE TRIGGER USER")

    inserted = 0
    skipped  = 0

    cur_src.execute(f'SELECT {col_list} FROM {table}')

    while True:
        batch = cur_src.fetchmany(BATCH_SIZE)
        if not batch:
            break

        rows = []
        for row in batch:
            values = []
            for val in row:
                # dicts e lists são campos JSONB — serializar para string JSON
                # para que o psycopg2 consiga adaptar ao tipo jsonb do destino
                if isinstance(val, (dict, list)):
                    values.append(json.dumps(val))
                elif hasattr(val, "adapted"):
                    values.append(str(val))
                else:
                    values.append(val)
            rows.append(values)

        try:
            psycopg2.extras.execute_batch(cur_dst, insert_sql, rows, page_size=BATCH_SIZE)
            conn_dst.commit()
            inserted += len(rows)
        except Exception as exc:
            conn_dst.rollback()
            log.warning(f"    Batch erro em {table}: {exc}")
            # Tentar linha a linha para identificar o problema
            for row in rows:
                try:
                    cur_dst.execute(insert_sql, row)
                    conn_dst.commit()
                    inserted += 1
                except Exception:
                    conn_dst.rollback()
                    skipped += 1

        pct = round(inserted / rows_src * 100) if rows_src else 100
        log.info(f"    {inserted}/{rows_src} ({pct}%) inseridas...")

    # Reativar triggers de usuário
    cur_dst.execute(f"ALTER TABLE {table} ENABLE TRIGGER USER")
    conn_dst.commit()

    cur_src.close()
    cur_dst.close()

    rows_dst  = count_rows(conn_dst, table)
    duration  = round(time.perf_counter() - t0, 1)
    log.info(f"  ✓ {table}: {inserted} inseridas | {skipped} ignoradas | {duration}s")

    return {
        "rows_src": rows_src,
        "rows_dst": rows_dst,
        "inserted": inserted,
        "skipped":  skipped,
        "duration_s": duration,
    }


# ============================================================
# Pós-migração
# ============================================================

def rebuild_fts(conn_dst: psycopg2.extensions.connection) -> None:
    """
    Reconstrói os tsvectors em articles, compounds e targets.
    Verifica se a coluna fts existe antes de executar — se 06_fts.sql
    não foi aplicado com sucesso, pula silenciosamente.
    """
    log.info("Reconstruindo índices FTS (tsvector)...")
    cur = conn_dst.cursor()

    tables_cols = [
        ("articles",  "title"),
        ("compounds", "name"),
        ("targets",   "name"),
    ]

    for table, col in tables_cols:
        # Checar se coluna fts existe
        try:
            cur.execute("""
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name   = %s
                  AND column_name  = 'fts'
            """, (table,))
            conn_dst.commit()
            if not cur.fetchone():
                log.warning(f"  ! {table}: coluna 'fts' não existe — 06_fts.sql não foi aplicado. Pulando.")
                continue
        except Exception as exc:
            conn_dst.rollback()
            log.warning(f"  ! {table}: erro ao verificar coluna fts: {exc}")
            continue

        # Disparar triggers de fts via UPDATE
        try:
            cur.execute(f"UPDATE {table} SET {col} = {col}")
            n = cur.rowcount
            conn_dst.commit()
            log.info(f"  ✓ {table}: {n} linhas com fts reconstruído")
        except Exception as exc:
            conn_dst.rollback()
            log.warning(f"  ! {table} FTS: {exc}")

    cur.close()


def refresh_materialized_views(conn_dst: psycopg2.extensions.connection) -> None:
    """Atualiza as views materializadas no destino."""
    log.info("Atualizando views materializadas...")
    cur = conn_dst.cursor()

    views = [
        "mv_compound_profile",
        "mv_compound_articles",
        "mv_compound_full",
    ]
    for view in views:
        try:
            cur.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}")
            conn_dst.commit()
            log.info(f"  ✓ {view}")
        except Exception as exc:
            conn_dst.rollback()
            log.warning(f"  ! {view}: {exc} (pode não existir ainda)")

    cur.close()


def verify_migration(
    conn_src: psycopg2.extensions.connection,
    conn_dst: psycopg2.extensions.connection,
) -> bool:
    """Compara contagens de linhas entre local e destino."""
    log.info("Verificando integridade da migração...")
    all_ok = True

    for table in TABLE_ORDER:
        try:
            n_src = count_rows(conn_src, table)
        except Exception as exc:
            log.warning(f"  ? {table:<25} local=ERRO ({exc})")
            all_ok = False
            continue

        try:
            n_dst = count_rows(conn_dst, table)
        except Exception:
            log.warning(f"  ✗ {table:<25} local={n_src:>6}  destino=ERRO (tabela não existe)")
            all_ok = False
            continue

        ok   = n_src == n_dst
        icon = "✓" if ok else "✗"
        log.info(f"  {icon} {table:<25} local={n_src:>6}  destino={n_dst:>6}")
        if not ok:
            all_ok = False

    return all_ok


# ============================================================
# CLI
# ============================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="migrate_to_supabase.py",
        description="Migra o banco ChEMBL+PubMed local para o Supabase ou outro PostgreSQL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
exemplos:
  # Via variável de ambiente
  $env:DATABASE_URL="postgresql://postgres.xxx:senha@host.supabase.com:6543/postgres"
  python migrate_to_supabase.py

  # Via flag
  python migrate_to_supabase.py --target-url "postgresql://..."

  # Só ver quantas linhas existem (sem migrar)
  python migrate_to_supabase.py --dry-run

  # Pular recriação do schema
  python migrate_to_supabase.py --skip-schema

  # Migrar só compostos e artigos
  python migrate_to_supabase.py --only compounds --only articles
        """,
    )
    parser.add_argument(
        "--target-url",
        metavar="URL",
        default=os.environ.get("DATABASE_URL", ""),
        help="URL do banco destino. Default: $DATABASE_URL",
    )
    parser.add_argument(
        "--skip-schema",
        action="store_true",
        help="Não aplicar os arquivos init/*.sql (banco destino já tem as tabelas).",
    )
    parser.add_argument(
        "--only",
        metavar="TABLE",
        action="append",
        default=[],
        choices=TABLE_ORDER,
        help="Migrar apenas esta tabela (repetível: --only compounds --only articles).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Só contar linhas, sem migrar nada.",
    )
    parser.add_argument(
        "--no-fts",
        action="store_true",
        help="Pular reconstrução dos índices FTS.",
    )
    parser.add_argument(
        "--no-views",
        action="store_true",
        help="Pular refresh das views materializadas.",
    )
    return parser.parse_args()


# ============================================================
# Main
# ============================================================

def main() -> None:
    args = parse_args()

    if not args.target_url:
        log.error(
            "URL do banco destino não definida.\n"
            "Use: $env:DATABASE_URL='postgresql://...' python migrate_to_supabase.py\n"
            "Ou:  python migrate_to_supabase.py --target-url 'postgresql://...'"
        )
        sys.exit(1)

    tables = args.only if args.only else TABLE_ORDER

    # ── Conectar ──────────────────────────────────────────────
    log.info("=" * 58)
    log.info("MIGRAÇÃO ChEMBL+PubMed → Supabase")
    log.info("=" * 58)

    try:
        conn_src = connect_local()
    except Exception as exc:
        log.error(f"Não foi possível conectar ao banco LOCAL: {exc}")
        log.error("Verifique se o Docker está rodando: docker compose up -d")
        sys.exit(1)

    try:
        conn_dst = connect_target(args.target_url)
    except Exception as exc:
        log.error(f"Não foi possível conectar ao banco DESTINO: {exc}")
        sys.exit(1)

    # ── Dry-run ───────────────────────────────────────────────
    if args.dry_run:
        log.info("\nMODO DRY-RUN — nenhuma linha será migrada\n")
        log.info(f"{'Tabela':<25} {'Local':>8}  {'Destino':>8}")
        log.info("-" * 46)
        for table in tables:
            try:
                n_src = count_rows(conn_src, table)
                n_dst = count_rows(conn_dst, table)
                log.info(f"  {table:<23} {n_src:>8}  {n_dst:>8}")
            except Exception as exc:
                log.warning(f"  {table:<23} erro: {exc}")
        conn_src.close()
        conn_dst.close()
        return

    # ── Schema ────────────────────────────────────────────────
    if not args.skip_schema:
        apply_schema(conn_dst)
    else:
        log.info("Schema ignorado (--skip-schema).")

    # ── Migração por tabela ───────────────────────────────────
    log.info(f"\nMigrando {len(tables)} tabela(s)...")
    t_total = time.perf_counter()
    stats   = {}

    for table in tables:
        log.info(f"\n── {table} ──")
        try:
            stats[table] = migrate_table(conn_src, conn_dst, table, dry_run=False)
        except Exception as exc:
            log.error(f"  ERRO em {table}: {exc}")
            conn_dst.rollback()
            stats[table] = {"error": str(exc)}

    # ── Pós-migração ──────────────────────────────────────────
    log.info("")

    if not args.no_fts and not args.only:
        rebuild_fts(conn_dst)

    if not args.no_views and not args.only:
        refresh_materialized_views(conn_dst)

    # ── Verificação ───────────────────────────────────────────
    log.info("")
    ok = verify_migration(conn_src, conn_dst)

    # ── Resumo ────────────────────────────────────────────────
    total_s   = round(time.perf_counter() - t_total, 1)
    total_ins = sum(s.get("inserted", 0) for s in stats.values())
    total_skip= sum(s.get("skipped",  0) for s in stats.values())

    log.info("\n" + "=" * 58)
    log.info(f"CONCLUÍDO em {total_s}s")
    log.info(f"  Linhas inseridas : {total_ins}")
    log.info(f"  Linhas ignoradas : {total_skip} (já existiam no destino)")
    log.info(f"  Integridade      : {'✓ OK' if ok else '✗ DIVERGÊNCIAS — verifique os logs'}")
    log.info("=" * 58)

    conn_src.close()
    conn_dst.close()

    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()