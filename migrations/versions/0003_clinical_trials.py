"""clinical_trials — cacheia trials da ClinicalTrials.gov por composto

Revision ID: 0003_clinical_trials
Revises: 0002_seed_compounds
Create Date: 2026-05-18

Aplica `database/init/09_clinical_trials.sql`, que cria:

- enums: trial_status, trial_phase, trial_study_type, intervention_match_method
- função: handle_updated_at()
- tabelas: clinical_trials, compound_clinical_trials
- triggers: trg_clinical_trials_updated_at, trg_compound_clinical_trials_updated_at
- índices: 6 índices (status, sponsor, start_date, phases GIN, conditions GIN, chembl)
- view: v_compound_trials_summary

O SQL fonte é idempotente (IF NOT EXISTS / EXCEPTION WHEN duplicate_object),
então re-aplicar sobre um banco que já tem essas estruturas é no-op semântico.
Isso cobre o caso de quem rodou o baseline antigo (que usava glob e já
aplicava o 09) — o upgrade não duplica nada.

Como aplicar
------------
    alembic upgrade head

Por que cursor cru e não op.execute()
-------------------------------------
O arquivo SQL tem múltiplas statements e blocos PL/pgSQL com dollar-quoting
($$ ... $$). `op.execute()` aceita só uma statement por chamada e quebra os
delimitadores. Mesmo padrão usado em 0001_baseline.py.
"""

from pathlib import Path

from alembic import op


revision = "0003_clinical_trials"
down_revision = "0002_seed_compounds"
branch_labels = None
depends_on = None


_SQL_FILE = (
    Path(__file__).resolve().parents[2]
    / "database"
    / "init"
    / "09_clinical_trials.sql"
)


def upgrade() -> None:
    raw_conn = op.get_bind().connection
    cur = raw_conn.cursor()
    cur.execute(_SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    raw_conn = op.get_bind().connection
    cur = raw_conn.cursor()

    # Ordem importa: view depende das tabelas, tabelas dos enums.
    cur.execute("DROP VIEW IF EXISTS v_compound_trials_summary")
    cur.execute("DROP TABLE IF EXISTS compound_clinical_trials")
    cur.execute("DROP TABLE IF EXISTS clinical_trials")

    # handle_updated_at() é compartilhada — não dropa aqui, outras tabelas
    # podem estar usando. Se for a última usuária, fica órfã sem dano.

    cur.execute("DROP TYPE IF EXISTS intervention_match_method")
    cur.execute("DROP TYPE IF EXISTS trial_study_type")
    cur.execute("DROP TYPE IF EXISTS trial_phase")
    cur.execute("DROP TYPE IF EXISTS trial_status")
