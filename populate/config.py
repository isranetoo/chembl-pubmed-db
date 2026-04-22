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

def _resolve_db_config() -> dict:
    """
    Resolve a configuração do banco a partir de variáveis de ambiente.
    Retorna um dict compatível com psycopg2.connect(**config).
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

    # ── Modo 2: variáveis individuais + defaults locais ──────
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
# Formato: (chembl_id, nome_comum)
# IDs verificados diretamente no ChEMBL (max_phase=4)
# ============================================================

POPULAR_COMPOUNDS = [
    # ── Analgésicos / Anti-inflamatórios ──────────────────────
    ("CHEMBL25",     "Aspirin"),       # NSAID / antiagregante plaquetário
    ("CHEMBL521",    "Ibuprofen"),     # NSAID
    ("CHEMBL112",    "Paracetamol"),   # analgésico / antitérmico
    ("CHEMBL154",    "Naproxen"),      # NSAID

    # ── Sistema Nervoso Central ────────────────────────────────
    ("CHEMBL113",    "Caffeine"),      # estimulante
    ("CHEMBL12",     "Diazepam"),      # benzodiazepínico
    ("CHEMBL70",     "Morphine"),      # opioide
    ("CHEMBL41",     "Fluoxetine"),    # antidepressivo SSRI
    ("CHEMBL809",    "Sertraline"),    # antidepressivo SSRI

    # ── Cardiovascular ────────────────────────────────────────
    ("CHEMBL1464",   "Warfarin"),      # anticoagulante
    ("CHEMBL1491",   "Amlodipine"),    # bloqueador de canal de cálcio
    ("CHEMBL1237",   "Lisinopril"),    # inibidor da ECA
    ("CHEMBL191",    "Losartan"),      # antagonista do receptor de angiotensina II
    ("CHEMBL1064",   "Simvastatin"),   # estatina (HMG-CoA reductase)
    ("CHEMBL1487",   "Atorvastatin"),  # estatina (HMG-CoA reductase)
    ("CHEMBL192",    "Sildenafil"),    # inibidor PDE5

    # ── Metabólico / Endócrino ────────────────────────────────
    ("CHEMBL1431",   "Metformin"),     # antidiabético
    ("CHEMBL384467", "Dexamethasone"), # corticosteroide

    # ── Gastrointestinal ──────────────────────────────────────
    ("CHEMBL1503",   "Omeprazole"),    # inibidor de bomba de prótons

    # ── Antimicrobianos / Antivirais ──────────────────────────
    ("CHEMBL1082",   "Amoxicillin"),   # antibiótico betalactâmico
    ("CHEMBL8",      "Ciprofloxacin"), # antibiótico fluoroquinolona
    ("CHEMBL1229",   "Oseltamivir"),   # antiviral (inibidor de neuraminidase)

    # ── Oncologia ─────────────────────────────────────────────
    ("CHEMBL83",     "Tamoxifen"),     # antagonista de receptor de estrogênio
    ("CHEMBL941",    "Imatinib"),      # inibidor de tirosina quinase (BCR-ABL)
]