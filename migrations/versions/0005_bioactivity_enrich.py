"""bioactivity_enrich — pchembl, assay metadata, ligand efficiency, variants

Revision ID: 0005_bioactivity_enrich
Revises: 0004_compound_metadata
Create Date: 2026-05-18

Aplica `database/init/11_bioactivity_enrich.sql`, que adiciona:

- 21 novas colunas em bioactivities (activity_id, pchembl_value,
  assay_*, document_*, BEI/LE/LLE/SEI, target_organism/tax_id,
  flags de qualidade, variantes de assay)
- índice UNIQUE parcial em activity_id (NULLs coexistem)
- índices em pchembl_value, assay_type, document_year, variant_mutation
- view v_top_potent_activities (pChEMBL ≥ 7)

O SQL fonte é idempotente (ADD COLUMN IF NOT EXISTS / CREATE INDEX
IF NOT EXISTS), então re-execução é no-op.
"""

from pathlib import Path

from alembic import op


revision = "0005_bioactivity_enrich"
down_revision = "0004_compound_metadata"
branch_labels = None
depends_on = None


_SQL_FILE = (
    Path(__file__).resolve().parents[2]
    / "database"
    / "init"
    / "11_bioactivity_enrich.sql"
)


def upgrade() -> None:
    raw_conn = op.get_bind().connection
    cur = raw_conn.cursor()
    cur.execute(_SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raw_conn = op.get_bind().connection
    cur = raw_conn.cursor()

    cur.execute("DROP VIEW  IF EXISTS v_top_potent_activities")
    cur.execute("DROP INDEX IF EXISTS ux_bioactivities_activity_id")

    for col in (
        "activity_id", "pchembl_value", "standard_value", "standard_units",
        "assay_chembl_id", "assay_description", "assay_type", "bao_label",
        "target_organism", "target_tax_id",
        "document_chembl_id", "document_journal", "document_year",
        "bei", "le", "lle", "sei",
        "data_validity_comment", "activity_comment", "potential_duplicate",
        "assay_variant_accession", "assay_variant_mutation",
    ):
        cur.execute(f"ALTER TABLE bioactivities DROP COLUMN IF EXISTS {col}")
