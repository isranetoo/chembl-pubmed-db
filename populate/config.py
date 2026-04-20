"""
config.py
---------
Constantes globais, configuração do banco e lista de compostos.
Importado por todos os outros módulos.
"""

import logging

# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

# ============================================================
# Banco de dados
# ============================================================

DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "chembl_pubmed",
    "user":     "admin",
    "password": "admin123",
}

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
    ("CHEMBL139",    "Diclofenac"),    # NSAID (derivado acético)
    ("CHEMBL118",    "Celecoxib"),     # inibidor seletivo de COX-2

    # ── Sistema Nervoso Central ────────────────────────────────
    ("CHEMBL113",    "Caffeine"),      # estimulante
    ("CHEMBL12",     "Diazepam"),      # benzodiazepínico
    ("CHEMBL70",     "Morphine"),      # opioide
    ("CHEMBL41",     "Fluoxetine"),    # antidepressivo SSRI
    ("CHEMBL809",    "Sertraline"),    # antidepressivo SSRI
    ("CHEMBL637",    "Venlafaxine"),   # antidepressivo SNRI
    ("CHEMBL715",    "Olanzapine"),    # antipsicótico atípico

    # ── Cardiovascular ────────────────────────────────────────
    ("CHEMBL1464",   "Warfarin"),      # anticoagulante
    ("CHEMBL1491",   "Amlodipine"),    # bloqueador de canal de cálcio
    ("CHEMBL1237",   "Lisinopril"),    # inibidor da ECA
    ("CHEMBL191",    "Losartan"),      # antagonista do receptor de angiotensina II
    ("CHEMBL1064",   "Simvastatin"),   # estatina (HMG-CoA reductase)
    ("CHEMBL1487",   "Atorvastatin"),  # estatina (HMG-CoA reductase)
    ("CHEMBL1496",   "Rosuvastatin"),  # estatina (HMG-CoA reductase)
    ("CHEMBL192",    "Sildenafil"),    # inibidor PDE5
    ("CHEMBL13",     "Metoprolol"),    # beta-bloqueador seletivo β1
    ("CHEMBL35",     "Furosemide"),    # diurético de alça
    ("CHEMBL1393",   "Spironolactone"),# antagonista da aldosterona
    ("CHEMBL1771",   "Clopidogrel"),   # antiagregante plaquetário (P2Y12)

    # ── Metabólico / Endócrino ────────────────────────────────
    ("CHEMBL1431",   "Metformin"),     # antidiabético (biguanida)
    ("CHEMBL384467", "Dexamethasone"), # corticosteroide
    ("CHEMBL595",    "Pioglitazone"),  # agonista PPAR-γ (tiazolidinediona)

    # ── Gastrointestinal ──────────────────────────────────────
    ("CHEMBL1503",   "Omeprazole"),    # inibidor de bomba de prótons
    ("CHEMBL46",     "Ondansetron"),   # antagonista 5-HT3 (antiemético)

    # ── Respiratório ──────────────────────────────────────────
    ("CHEMBL714",    "Salbutamol"),    # agonista β2 (broncodilatador)
    ("CHEMBL787",    "Montelukast"),   # antagonista de receptor de leucotrieno

    # ── Antimicrobianos / Antivirais ──────────────────────────
    ("CHEMBL1082",   "Amoxicillin"),   # antibiótico betalactâmico
    ("CHEMBL8",      "Ciprofloxacin"), # antibiótico fluoroquinolona
    ("CHEMBL137",    "Metronidazole"), # nitroimidazol (antibact. / antiprotoz.)
    ("CHEMBL529",    "Azithromycin"),  # antibiótico macrolídeo
    ("CHEMBL1229",   "Oseltamivir"),   # antiviral (inibidor de neuraminidase)

    # ── Antifúngicos ──────────────────────────────────────────
    ("CHEMBL106",    "Fluconazole"),   # antifúngico triazólico

    # ── Oncologia ─────────────────────────────────────────────
    ("CHEMBL83",     "Tamoxifen"),     # antagonista de receptor de estrogênio
    ("CHEMBL941",    "Imatinib"),      # inibidor de tirosina quinase (BCR-ABL)
    ("CHEMBL553",    "Erlotinib"),     # inibidor de tirosina quinase (EGFR)
    ("CHEMBL428647", "Paclitaxel"),    # estabilizador de microtúbulo (taxano)
]