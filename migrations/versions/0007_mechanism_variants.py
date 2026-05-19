"""mechanism_variants — variant_sequence em mechanisms

Revision ID: 0007_mechanism_variants
Revises: 0006_target_enrich
Create Date: 2026-05-18

Aplica `database/init/13_mechanism_variants.sql`, que adiciona:

- mechanisms.variant_sequence JSONB (info de mutação associada
  ao mecanismo — essencial pra resistência mutacional)
- índice em variant_sequence->>'mutation'
- view v_mechanism_variants
"""

from pathlib import Path

from alembic import op


revision = "0007_mechanism_variants"
down_revision = "0006_target_enrich"
branch_labels = None
depends_on = None


_SQL_FILE = (
    Path(__file__).resolve().parents[2]
    / "database"
    / "init"
    / "13_mechanism_variants.sql"
)


def upgrade() -> None:
    raw_conn = op.get_bind().connection
    cur = raw_conn.cursor()
    cur.execute(_SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raw_conn = op.get_bind().connection
    cur = raw_conn.cursor()

    cur.execute("DROP VIEW  IF EXISTS v_mechanism_variants")
    cur.execute("ALTER TABLE mechanisms DROP COLUMN IF EXISTS variant_sequence")
