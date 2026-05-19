"""target_enrich — tax_id, components, xrefs (PDB/GO/UniProt/Reactome)

Revision ID: 0006_target_enrich
Revises: 0005_bioactivity_enrich
Create Date: 2026-05-18

Aplica `database/init/12_target_enrich.sql`, que adiciona:

- targets.tax_id, species_group_flag
- tabela target_components (accession UniProt, gene_symbol, type)
- tabela target_xrefs (PDB, GO, Reactome, InterPro, Pfam, HGNC, …)
- views v_target_genes, v_target_pdbs, v_target_go

O SQL fonte é idempotente (ADD COLUMN IF NOT EXISTS / CREATE TABLE
IF NOT EXISTS / CREATE INDEX IF NOT EXISTS).
"""

from pathlib import Path

from alembic import op


revision = "0006_target_enrich"
down_revision = "0005_bioactivity_enrich"
branch_labels = None
depends_on = None


_SQL_FILE = (
    Path(__file__).resolve().parents[2]
    / "database"
    / "init"
    / "12_target_enrich.sql"
)


def upgrade() -> None:
    raw_conn = op.get_bind().connection
    cur = raw_conn.cursor()
    cur.execute(_SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raw_conn = op.get_bind().connection
    cur = raw_conn.cursor()

    cur.execute("DROP VIEW  IF EXISTS v_target_go")
    cur.execute("DROP VIEW  IF EXISTS v_target_pdbs")
    cur.execute("DROP VIEW  IF EXISTS v_target_genes")
    cur.execute("DROP TABLE IF EXISTS target_xrefs")
    cur.execute("DROP TABLE IF EXISTS target_components")

    for col in ("tax_id", "species_group_flag"):
        cur.execute(f"ALTER TABLE targets DROP COLUMN IF EXISTS {col}")
