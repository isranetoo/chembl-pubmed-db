"""compound_metadata — campos clínicos/regulatórios + synonyms + ATC

Revision ID: 0004_compound_metadata
Revises: 0003_clinical_trials
Create Date: 2026-05-18

Aplica `database/init/10_compound_metadata.sql`, que adiciona:

- novas colunas em compounds (max_phase, first_approval, vias de
  administração, withdrawn_*, prodrug/natural_product/first_in_class/orphan,
  chirality, usan_stem/definition/year, inchi, np_likeness_score,
  black_box_warning, therapeutic_flag, availability_type)
- tabela compound_synonyms (INN, BAN, USAN, trade names, research codes)
- tabela compound_atc (classificação ATC da WHO, 5 níveis)
- índices para filtros frequentes
- view v_compound_clinical (perfil clínico consolidado)

O SQL fonte é idempotente (ADD COLUMN IF NOT EXISTS / CREATE TABLE
IF NOT EXISTS / CREATE INDEX IF NOT EXISTS), então re-execução
sobre banco já migrado é no-op.
"""

from pathlib import Path

from alembic import op


revision = "0004_compound_metadata"
down_revision = "0003_clinical_trials"
branch_labels = None
depends_on = None


_SQL_FILE = (
    Path(__file__).resolve().parents[2]
    / "database"
    / "init"
    / "10_compound_metadata.sql"
)


def upgrade() -> None:
    raw_conn = op.get_bind().connection
    cur = raw_conn.cursor()
    cur.execute(_SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raw_conn = op.get_bind().connection
    cur = raw_conn.cursor()

    cur.execute("DROP VIEW  IF EXISTS v_compound_clinical")
    cur.execute("DROP TABLE IF EXISTS compound_atc")
    cur.execute("DROP TABLE IF EXISTS compound_synonyms")

    # Remove colunas adicionadas. ALTER TABLE DROP COLUMN IF EXISTS é
    # idempotente — seguro mesmo se a coluna nunca chegou a ser criada.
    for col in (
        "max_phase", "first_approval", "molecule_type",
        "oral", "parenteral", "topical",
        "black_box_warning",
        "withdrawn_flag", "withdrawn_reason", "withdrawn_year",
        "withdrawn_country", "withdrawn_class",
        "prodrug", "natural_product", "therapeutic_flag",
        "first_in_class", "orphan",
        "chirality", "availability_type",
        "usan_stem", "usan_stem_definition", "usan_year",
        "inchi", "np_likeness_score",
    ):
        cur.execute(f"ALTER TABLE compounds DROP COLUMN IF EXISTS {col}")
