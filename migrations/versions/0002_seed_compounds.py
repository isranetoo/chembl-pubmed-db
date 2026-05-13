"""seed_compounds — lista de compostos populares migra do código para o banco

Revision ID: 0002_seed_compounds
Revises: 0001_baseline
Create Date: 2026-05-13

Antes desta migration a lista de ~51 compostos populares vivia hardcoded em
`populate/config.py` (`POPULAR_COMPOUNDS`). Cada adição/remoção exigia commit
e deploy.

Agora a lista vive em `seed_compounds`:

    chembl_id    TEXT PRIMARY KEY
    common_name  TEXT NOT NULL
    category     TEXT          -- agrupamento terapêutico
    is_active    BOOLEAN       -- desativar sem deletar (preserva histórico)
    added_at     TIMESTAMP

Adicionar um composto:
    INSERT INTO seed_compounds (chembl_id, common_name, category)
    VALUES ('CHEMBL999', 'Foo', 'Oncologia');

Desativar (não roda mais no populate, mas mantém registro):
    UPDATE seed_compounds SET is_active = FALSE WHERE chembl_id = 'CHEMBL999';
"""

from alembic import op


revision = "0002_seed_compounds"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


# Seed inicial — extraído de populate/config.py:POPULAR_COMPOUNDS.
# Mantém ordem e categorias dos comentários originais.
_SEED: list[tuple[str, str, str]] = [
    # Analgésicos / Anti-inflamatórios
    ("CHEMBL25",       "Aspirin",            "Analgésicos"),
    ("CHEMBL521",      "Ibuprofen",          "Analgésicos"),
    ("CHEMBL112",      "Paracetamol",        "Analgésicos"),
    ("CHEMBL154",      "Naproxen",           "Analgésicos"),
    ("CHEMBL599",      "Meloxicam",          "Analgésicos"),
    ("CHEMBL1237044",  "Tramadol",           "Analgésicos"),

    # Sistema Nervoso Central
    ("CHEMBL113",      "Caffeine",           "Sistema Nervoso Central"),
    ("CHEMBL12",       "Diazepam",           "Sistema Nervoso Central"),
    ("CHEMBL661",      "Alprazolam",         "Sistema Nervoso Central"),
    ("CHEMBL70",       "Morphine",           "Sistema Nervoso Central"),
    ("CHEMBL41",       "Fluoxetine",         "Sistema Nervoso Central"),
    ("CHEMBL809",      "Sertraline",         "Sistema Nervoso Central"),
    ("CHEMBL1009",     "Levodopa",           "Sistema Nervoso Central"),
    ("CHEMBL502",      "Donepezil",          "Sistema Nervoso Central"),
    ("CHEMBL940",      "Gabapentin",         "Sistema Nervoso Central"),
    ("CHEMBL1059",     "Pregabalin",         "Sistema Nervoso Central"),
    ("CHEMBL54",       "Haloperidol",        "Sistema Nervoso Central"),
    ("CHEMBL716",      "Quetiapine",         "Sistema Nervoso Central"),
    ("CHEMBL911",      "Zolpidem",           "Sistema Nervoso Central"),
    ("CHEMBL1200826",  "Lithium carbonate",  "Sistema Nervoso Central"),

    # Cardiovascular
    ("CHEMBL1464",     "Warfarin",           "Cardiovascular"),
    ("CHEMBL1491",     "Amlodipine",         "Cardiovascular"),
    ("CHEMBL193",      "Nifedipine",         "Cardiovascular"),
    ("CHEMBL1237",     "Lisinopril",         "Cardiovascular"),
    ("CHEMBL578",      "Enalapril",          "Cardiovascular"),
    ("CHEMBL191",      "Losartan",           "Cardiovascular"),
    ("CHEMBL1069",     "Valsartan",          "Cardiovascular"),
    ("CHEMBL1064",     "Simvastatin",        "Cardiovascular"),
    ("CHEMBL1487",     "Atorvastatin",       "Cardiovascular"),
    ("CHEMBL192",      "Sildenafil",         "Cardiovascular"),
    ("CHEMBL27",       "Propranolol",        "Cardiovascular"),
    ("CHEMBL1751",     "Digoxin",            "Cardiovascular"),

    # Metabólico / Endócrino
    ("CHEMBL1431",     "Metformin",          "Metabólico"),
    ("CHEMBL384467",   "Dexamethasone",      "Metabólico"),
    ("CHEMBL1422",     "Sitagliptin",        "Metabólico"),
    ("CHEMBL2107830",  "Empagliflozin",      "Metabólico"),

    # Gastrointestinal
    ("CHEMBL1503",     "Omeprazole",         "Gastrointestinal"),
    ("CHEMBL1502",     "Pantoprazole",       "Gastrointestinal"),

    # Antimicrobianos
    ("CHEMBL1082",     "Amoxicillin",        "Antimicrobianos"),
    ("CHEMBL8",        "Ciprofloxacin",      "Antimicrobianos"),
    ("CHEMBL1433",     "Doxycycline",        "Antimicrobianos"),
    ("CHEMBL262777",   "Vancomycin",         "Antimicrobianos"),

    # Antivirais
    ("CHEMBL1229",     "Oseltamivir",        "Antivirais"),
    ("CHEMBL1486",     "Tenofovir",          "Antivirais"),
    ("CHEMBL223228",   "Efavirenz",          "Antivirais"),

    # Oncologia
    ("CHEMBL83",       "Tamoxifen",          "Oncologia"),
    ("CHEMBL941",      "Imatinib",           "Oncologia"),
    ("CHEMBL34259",    "Methotrexate",       "Oncologia"),
    ("CHEMBL1773",     "Capecitabine",       "Oncologia"),
    ("CHEMBL1351",     "Carboplatin",        "Oncologia"),

    # Respiratório
    ("CHEMBL1900528",  "Tiotropium",         "Respiratório"),
    ("CHEMBL1473",     "Fluticasone",        "Respiratório"),
]


def upgrade() -> None:
    raw_conn = op.get_bind().connection
    cur = raw_conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS seed_compounds (
            chembl_id    TEXT PRIMARY KEY,
            common_name  TEXT NOT NULL,
            category     TEXT,
            is_active    BOOLEAN NOT NULL DEFAULT TRUE,
            added_at     TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_seed_compounds_active "
        "ON seed_compounds(is_active)"
    )

    # ON CONFLICT torna a migration idempotente: re-aplicar não duplica nem
    # sobrescreve edições manuais (e.g., common_name corrigido pelo operador).
    cur.executemany(
        "INSERT INTO seed_compounds (chembl_id, common_name, category) "
        "VALUES (%s, %s, %s) "
        "ON CONFLICT (chembl_id) DO NOTHING",
        _SEED,
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS seed_compounds")
