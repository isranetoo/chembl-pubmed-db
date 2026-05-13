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


def upgrade() -> None:
    """Executa os SQLs de bootstrap na ordem numérica."""
    raw_conn = op.get_bind().connection
    cur = raw_conn.cursor()

    for sql_path in sorted(INIT_DIR.glob("*.sql")):
        sql = sql_path.read_text(encoding="utf-8")
        # psycopg2 aceita múltiplas statements em uma única chamada execute().
        cur.execute(sql)


def downgrade() -> None:
    """
    Não há downgrade do baseline: derrubar tudo apagaria dados.
    Para reverter, derrube o banco/volume e recrie do zero.
    """
    raise NotImplementedError(
        "Baseline não pode ser revertido automaticamente. "
        "Derrube o banco/volume e recrie."
    )
