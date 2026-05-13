"""
config.py
---------
Constantes globais, configuração do banco e lista de compostos.
Importado por todos os outros módulos.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# ============================================================
# Logging — console + arquivo com timestamp
# ============================================================

def _setup_logging() -> Path:
    """
    Configura o root logger com dois handlers:
      - StreamHandler  → console (stdout)
      - FileHandler    → logs/populate_YYYY-MM-DD_HHhMM.log

    Retorna o caminho do arquivo de log criado.
    Idempotente: não adiciona handlers duplicados se chamado mais de uma vez.
    """
    LOG_DIR = Path(__file__).parent / "logs"
    LOG_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%Hh%M")
    log_file  = LOG_DIR / f"populate_{timestamp}.log"

    fmt     = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
    datefmt = "%H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt=datefmt)

    root = logging.getLogger()
    if root.handlers:          # já configurado — não duplicar
        return log_file

    root.setLevel(logging.INFO)

    # Console
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    root.addHandler(console)

    # Arquivo
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    return log_file


_log_file = _setup_logging()

# Disponível para outros módulos que queiram exibir o caminho do log
LOG_FILE: Path = _log_file

# ============================================================
# Banco de dados
# ============================================================
#
# Configuração resolvida nesta ordem de prioridade:
#
#   1. DATABASE_URL  (Supabase, Railway, Render, Heroku...)
#        postgresql://user:pass@host:5432/dbname
#        postgresql://user:pass@host:5432/dbname?sslmode=require
#
#   2. Variáveis individuais (qualquer banco)
#        DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_SSLMODE
#
#   3. Defaults para o Docker local
#        localhost:5432 / chembl_pubmed / admin / admin123
#
# Exemplos de uso:
#
#   # Docker local (sem variáveis — usa defaults)
#   python populate.py
#
#   # Supabase
#   $env:DATABASE_URL="postgresql://postgres.xxx:senha@aws-0-sa-east-1.pooler.supabase.com:5432/postgres"
#   python populate.py
#
#   # Outra instância PostgreSQL
#   $env:DB_HOST="meu-servidor.com"; $env:DB_PASSWORD="senha"
#   python populate.py

import os
from urllib.parse import urlparse

# Ambientes considerados "dev" — defaults inseguros (admin/admin123) só funcionam aqui.
# Setar APP_ENV=production (ou staging/prod) força configuração explícita do banco.
_DEV_ENVS = {"development", "dev", "local", "test"}
_INDIVIDUAL_DB_VARS = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD", "DB_SSLMODE")


def app_env() -> str:
    """Retorna APP_ENV em lower-case; default 'development'."""
    return os.environ.get("APP_ENV", "development").strip().lower()


def is_dev() -> bool:
    """True se APP_ENV indica ambiente de desenvolvimento/teste."""
    return app_env() in _DEV_ENVS


def _resolve_db_config() -> dict:
    """
    Resolve a configuração do banco a partir de variáveis de ambiente.
    Retorna um dict compatível com psycopg2.connect(**config).

    Estratégia de segurança:
      - Em ambiente NÃO-dev, exige DATABASE_URL ou alguma var individual.
      - Os defaults locais (admin/admin123/localhost) só são aplicados em
        APP_ENV=development|dev|local|test. Caso contrário levanta RuntimeError.
    """
    database_url = os.environ.get("DATABASE_URL", "").strip()

    if database_url:
        # ── Modo 1: DATABASE_URL ─────────────────────────────
        # Supabase e maioria dos PaaS usam este formato.
        parsed = urlparse(database_url)
        config = {
            "host":     parsed.hostname,
            "port":     parsed.port or 5432,
            "dbname":   parsed.path.lstrip("/"),
            "user":     parsed.username,
            "password": parsed.password,
        }
        # Parâmetros extras da query string (ex: sslmode=require)
        if parsed.query:
            for param in parsed.query.split("&"):
                if "=" in param:
                    k, v = param.split("=", 1)
                    config[k] = v

        # Supabase exige SSL — garantir mesmo que não esteja na URL
        if "supabase" in (parsed.hostname or ""):
            config.setdefault("sslmode", "require")

        return config

    # ── Modo 2: variáveis individuais ─────────────────────────
    any_individual_set = any(os.environ.get(v) for v in _INDIVIDUAL_DB_VARS)

    if not any_individual_set and not is_dev():
        raise RuntimeError(
            f"Configuração de banco ausente: APP_ENV={app_env()!r} mas nenhuma "
            "das variáveis DATABASE_URL ou DB_HOST/DB_PORT/DB_NAME/DB_USER/"
            "DB_PASSWORD/DB_SSLMODE foi definida. Os defaults locais "
            "(localhost/admin/admin123) só funcionam em APP_ENV="
            f"{sorted(_DEV_ENVS)}. Defina DATABASE_URL=postgresql://... ou as "
            "variáveis individuais antes de iniciar o serviço."
        )

    return {
        "host":     os.environ.get("DB_HOST",     "localhost"),
        "port":     int(os.environ.get("DB_PORT", "5432")),
        "dbname":   os.environ.get("DB_NAME",     "chembl_pubmed"),
        "user":     os.environ.get("DB_USER",     "admin"),
        "password": os.environ.get("DB_PASSWORD", "admin123"),
        **({} if not os.environ.get("DB_SSLMODE")
           else {"sslmode": os.environ["DB_SSLMODE"]}),
    }


DB_CONFIG: dict = _resolve_db_config()

# ============================================================
# APIs
# ============================================================

CHEMBL_BASE  = "https://www.ebi.ac.uk/chembl/api/data"
PUBMED_BASE  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# ============================================================
# Limites por composto
# ============================================================

MAX_BIOACT   = 5   # bioatividades buscadas no ChEMBL
MAX_ARTICLES = 5   # artigos buscados no PubMed

# ============================================================
# Compostos populares
# ============================================================
# A lista vive na tabela `seed_compounds` no banco (migration
# 0002_seed_compounds). Use `populate.db.load_popular_compounds()`
# para lê-la em runtime. Para adicionar/desativar um composto:
#
#     INSERT INTO seed_compounds (chembl_id, common_name, category)
#     VALUES ('CHEMBL999', 'Foo', 'Oncologia');
#
#     UPDATE seed_compounds SET is_active = FALSE
#     WHERE chembl_id = 'CHEMBL999';
