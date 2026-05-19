"""owkin_histopathology — tabelas de TME/TCGA via Owkin

Revision ID: 0008_owkin_histopathology
Revises: 0007_mechanism_variants
Create Date: 2026-05-19

Aplica `database/init/08_owkin_histopathology.sql`, que cria:

- indication_tcga_map        — mapeamento indicação → coorte TCGA
- owkin_cohort_stats         — cache de stats TME por coorte/feature
- owkin_slides               — top slides ranqueados por feature
- tcga_cohort_dictionary     — seed com 26 coortes TCGA + keywords
- v_compounds_with_histopathology, v_tme_summary — views

Em fresh installs essas tabelas já são criadas pelos arquivos
`database/init/*.sql` (Docker entrypoint). Esta migration é o
caminho oficial para bancos existentes — alembic upgrade head.

O SQL é idempotente (IF NOT EXISTS + ON CONFLICT DO NOTHING),
então re-execução é segura.
"""

from pathlib import Path

from alembic import op


revision = "0008_owkin_histopathology"
down_revision = "0007_mechanism_variants"
branch_labels = None
depends_on = None


_SQL_FILE = (
    Path(__file__).resolve().parents[2]
    / "database"
    / "init"
    / "08_owkin_histopathology.sql"
)


def upgrade() -> None:
    raw_conn = op.get_bind().connection
    cur = raw_conn.cursor()
    cur.execute(_SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raw_conn = op.get_bind().connection
    cur = raw_conn.cursor()

    cur.execute("DROP VIEW  IF EXISTS v_tme_summary")
    cur.execute("DROP VIEW  IF EXISTS v_compounds_with_histopathology")
    cur.execute("DROP TABLE IF EXISTS owkin_slides")
    cur.execute("DROP TABLE IF EXISTS owkin_cohort_stats")
    cur.execute("DROP TABLE IF EXISTS indication_tcga_map")
    cur.execute("DROP TABLE IF EXISTS tcga_cohort_dictionary")
