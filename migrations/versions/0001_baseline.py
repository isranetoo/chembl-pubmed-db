"""baseline — schema atual capturado a partir de database/init/*.sql

Revision ID: 0001_baseline
Revises:
Create Date: 2026-05-13

Este baseline representa o estado do schema produzido pelos 8 arquivos
em database/init/ (01_schema → 08_owkin_histopathology). A partir daqui,
toda alteração de schema deve virar uma migration Alembic dedicada via
`alembic revision -m "<descrição>"`.

Como aplicar
------------
1. Banco NOVO (sem nenhuma tabela):
       alembic upgrade head
   O baseline executa os 8 SQLs em ordem.

2. Banco que JÁ tem o schema (criado via docker-compose, por exemplo):
       alembic stamp head
   Marca o baseline como aplicado SEM executar o SQL — evita CREATE TABLE
   duplicado.

Detalhe técnico
---------------
Os arquivos .sql contêm múltiplas statements e usam construções
específicas de PostgreSQL (PL/pgSQL, dollar-quoting, triggers). Por isso
executamos via psycopg2 cursor cru — `op.execute()` só lida com uma
statement por chamada e não respeita os delimitadores `$$ ... $$`.
"""

from pathlib import Path

from alembic import op


# revision identifiers, used by Alembic.
revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


# Pasta dos SQLs originais — preserva-os como fonte de verdade do baseline.
INIT_DIR = Path(__file__).resolve().parents[2] / "database" / "init"


# Arquivos congelados como parte do baseline. Qualquer SQL novo em
# `database/init/` (09 em diante) deve virar uma migration Alembic dedicada —
# não estende esta lista. Veja 0003_clinical_trials.py como exemplo.
_BASELINE_SQL_FILES = (
    "01_schema.sql",
    "02_article_enrich.sql",
    "03_indications.sql",
    "04_mechanisms.sql",
    "05_admet.sql",
    "06_fts.sql",
    "07_materialized_views.sql",
    "08_owkin_histopathology.sql",
)

_BASELINE_TABLES = (
    "compounds",
    "targets",
    "bioactivities",
    "articles",
    "article_compounds",
    "indications",
    "mechanisms",
    "admet_properties",
    "indication_tcga_map",  # created by 08_owkin_histopathology.sql
)

# Tables created by 01_schema.sql through 07_materialized_views.sql.
# If all of these exist the core schema is already in place; we can safely
# apply the remaining SQL files (which use CREATE … IF NOT EXISTS).
_CORE_TABLES = frozenset({
    "compounds", "targets", "bioactivities", "articles",
    "article_compounds", "indications", "mechanisms", "admet_properties",
})


def _existing_baseline_tables(cur) -> set[str]:
    cur.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = ANY(%s)
        """,
        (list(_BASELINE_TABLES),),
    )
    return {row[0] for row in cur.fetchall()}


def upgrade() -> None:
    """Executa os SQLs de bootstrap na ordem numérica."""
    raw_conn = op.get_bind().connection
    cur = raw_conn.cursor()

    existing = _existing_baseline_tables(cur)

    if existing == set(_BASELINE_TABLES):
        # Banco completamente inicializado — no-op.
        return

    if not existing:
        # Banco vazio — executa os SQLs do baseline na ordem numérica.
        # SQLs posteriores (09+) são aplicados pelas próprias migrations.
        for filename in _BASELINE_SQL_FILES:
            sql_path = INIT_DIR / filename
            cur.execute(sql_path.read_text(encoding="utf-8"))
        return

    if _CORE_TABLES.issubset(existing):
        # Schema core existe (criado via docker-compose ou versão anterior).
        # Apenas as tabelas suplementares (08_owkin_histopathology.sql) estão
        # faltando. Esse arquivo usa CREATE … IF NOT EXISTS, portanto é seguro
        # aplicá-lo agora sem risco de duplicar as demais tabelas.
        owkin_sql = INIT_DIR / "08_owkin_histopathology.sql"
        cur.execute(owkin_sql.read_text(encoding="utf-8"))
        return

    missing = sorted(set(_BASELINE_TABLES) - existing)
    found = sorted(existing)
    raise RuntimeError(
        "Schema parcial detectado: algumas tabelas do baseline já existem, "
        "mas o banco não parece completamente inicializado. "
        f"Encontradas: {found}. Ausentes: {missing}. "
        "Recrie o banco/volume ou alinhe o schema antes de rodar Alembic."
    )


def downgrade() -> None:
    """
    Não há downgrade do baseline: derrubar tudo apagaria dados.
    Para reverter, derrube o banco/volume e recrie do zero.
    """
    raise NotImplementedError(
        "Baseline não pode ser revertido automaticamente. "
        "Derrube o banco/volume e recrie."
    )
