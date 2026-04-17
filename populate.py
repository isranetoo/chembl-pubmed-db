"""
populate_v1.py  —  versao original
-----------------------------------
Popula o banco com compostos do ChEMBL e artigos do PubMed.

Diferencas em relacao a v2:
  - Artigos buscados via esummary (JSON) — sem abstract
  - Sem termos MeSH, keywords nem pub_types
  - Sem indicacoes terapeuticas

Uso:
    pip install -r requirements.txt
    python populate_v1.py
"""

import json
import logging
import time
from typing import Optional

import psycopg2
import requests

# ------------------------------------------------------------
# Configuracao
# ------------------------------------------------------------
DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "chembl_pubmed",
    "user":     "admin",
    "password": "admin123",
}

POPULAR_COMPOUNDS = [
    ("CHEMBL25",   "Aspirin"),
    ("CHEMBL521",  "Ibuprofen"),
    ("CHEMBL112",  "Paracetamol"),
    ("CHEMBL113",  "Caffeine"),
    ("CHEMBL1431", "Metformin"),
    ("CHEMBL1487", "Atorvastatin"),
    ("CHEMBL1503", "Omeprazole"),
    ("CHEMBL1082", "Amoxicillin"),
    ("CHEMBL12",   "Diazepam"),
    ("CHEMBL70",   "Morphine"),
]

CHEMBL_BASE   = "https://www.ebi.ac.uk/chembl/api/data"
PUBMED_BASE   = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
MAX_BIOACT    = 5
MAX_ARTICLES  = 5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ============================================================
# ChEMBL
# ============================================================

def fetch_compound(chembl_id: str) -> Optional[dict]:
    try:
        r = requests.get(f"{CHEMBL_BASE}/molecule/{chembl_id}.json", timeout=20)
        r.raise_for_status()
        data    = r.json()
        props   = data.get("molecule_properties") or {}
        structs = data.get("molecule_structures") or {}
        return {
            "chembl_id":         chembl_id,
            "name":              data.get("pref_name") or chembl_id,
            "molecular_formula": props.get("full_molformula"),
            "mol_weight":        props.get("full_mwt"),
            "smiles":            structs.get("canonical_smiles"),
            "inchi_key":         structs.get("standard_inchi_key"),
            "alogp":             props.get("alogp"),
            "hbd":               props.get("hbd"),
            "hba":               props.get("hba"),
            "psa":               props.get("psa"),
            "ro5_violations":    props.get("num_ro5_violations"),
        }
    except Exception as exc:
        log.error(f"Erro ao buscar composto {chembl_id}: {exc}")
        return None


def fetch_bioactivities(chembl_id: str) -> list:
    try:
        r = requests.get(
            f"{CHEMBL_BASE}/activity.json",
            params={"molecule_chembl_id": chembl_id, "limit": MAX_BIOACT},
            timeout=20,
        )
        r.raise_for_status()
        return r.json().get("activities", [])
    except Exception as exc:
        log.error(f"Erro ao buscar bioatividades de {chembl_id}: {exc}")
        return []


def fetch_target(target_chembl_id: str) -> Optional[dict]:
    try:
        r = requests.get(f"{CHEMBL_BASE}/target/{target_chembl_id}.json", timeout=20)
        r.raise_for_status()
        data = r.json()
        return {
            "chembl_id": target_chembl_id,
            "name":      data.get("pref_name") or target_chembl_id,
            "type":      data.get("target_type"),
            "organism":  data.get("organism"),
        }
    except Exception as exc:
        log.error(f"Erro ao buscar alvo {target_chembl_id}: {exc}")
        return None


# ============================================================
# PubMed  —  esummary (JSON, sem abstract)
# ============================================================

def search_pubmed(compound_name: str) -> list:
    """Retorna lista de PMIDs para um composto."""
    try:
        r = requests.get(
            f"{PUBMED_BASE}/esearch.fcgi",
            params={
                "db":      "pubmed",
                "term":    f"{compound_name}[Title/Abstract]",
                "retmax":  MAX_ARTICLES,
                "retmode": "json",
            },
            timeout=20,
        )
        r.raise_for_status()
        return r.json().get("esearchresult", {}).get("idlist", [])
    except Exception as exc:
        log.error(f"Erro ao buscar PubMed para '{compound_name}': {exc}")
        return []


def fetch_articles(pmids: list) -> list:
    """
    Busca metadados de artigos via esummary (JSON).
    Nao retorna abstract — use populate_v2.py para isso.
    """
    if not pmids:
        return []
    try:
        r = requests.get(
            f"{PUBMED_BASE}/esummary.fcgi",
            params={
                "db":      "pubmed",
                "id":      ",".join(pmids),
                "retmode": "json",
            },
            timeout=20,
        )
        r.raise_for_status()
        result   = r.json().get("result", {})
        articles = []
        for pmid in pmids:
            entry = result.get(pmid)
            if not entry or not isinstance(entry, dict):
                continue
            authors  = [a.get("name", "") for a in entry.get("authors", [])]
            pub_date = entry.get("pubdate", "")
            year     = None
            try:
                year = int(pub_date.split()[0])
            except Exception:
                pass
            doi = next(
                (x.get("value") for x in entry.get("articleids", [])
                 if x.get("idtype") == "doi"),
                None,
            )
            articles.append({
                "pmid":     pmid,
                "title":    entry.get("title"),
                "abstract": None,       # esummary nao retorna abstract
                "authors":  json.dumps(authors),
                "journal":  entry.get("source"),
                "pub_year": year,
                "doi":      doi,
            })
        return articles
    except Exception as exc:
        log.error(f"Erro ao buscar artigos: {exc}")
        return []


# ============================================================
# Insercoes no banco
# ============================================================

def upsert_compound(cur, data: dict) -> str:
    cur.execute(
        """
        INSERT INTO compounds
            (chembl_id, name, molecular_formula, mol_weight, smiles,
             inchi_key, alogp, hbd, hba, psa, ro5_violations)
        VALUES
            (%(chembl_id)s, %(name)s, %(molecular_formula)s, %(mol_weight)s,
             %(smiles)s, %(inchi_key)s, %(alogp)s, %(hbd)s, %(hba)s,
             %(psa)s, %(ro5_violations)s)
        ON CONFLICT (chembl_id) DO UPDATE
            SET name = EXCLUDED.name
        RETURNING id
        """,
        data,
    )
    return cur.fetchone()[0]


def upsert_target(cur, data: dict) -> str:
    cur.execute(
        """
        INSERT INTO targets (chembl_id, name, type, organism)
        VALUES (%(chembl_id)s, %(name)s, %(type)s, %(organism)s)
        ON CONFLICT (chembl_id) DO UPDATE
            SET name = EXCLUDED.name
        RETURNING id
        """,
        data,
    )
    return cur.fetchone()[0]


def insert_bioactivity(cur, compound_id: str, target_id: str, act: dict):
    cur.execute(
        """
        INSERT INTO bioactivities
            (compound_id, target_id, activity_type, value, units, relation)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            compound_id,
            target_id,
            act.get("type"),
            act.get("value"),
            act.get("units"),
            act.get("relation"),
        ),
    )


def upsert_article(cur, data: dict) -> str:
    cur.execute(
        """
        INSERT INTO articles
            (pmid, title, abstract, authors, journal, pub_year, doi)
        VALUES
            (%(pmid)s, %(title)s, %(abstract)s, %(authors)s::jsonb,
             %(journal)s, %(pub_year)s, %(doi)s)
        ON CONFLICT (pmid) DO UPDATE
            SET title = EXCLUDED.title
        RETURNING id
        """,
        data,
    )
    return cur.fetchone()[0]


def link_article_compound(cur, article_id: str, compound_id: str):
    cur.execute(
        """
        INSERT INTO article_compounds (article_id, compound_id)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
        """,
        (article_id, compound_id),
    )


# ============================================================
# Main
# ============================================================

def main():
    log.info("Conectando ao banco de dados...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur  = conn.cursor()

    for chembl_id, common_name in POPULAR_COMPOUNDS:
        log.info("=" * 55)
        log.info(f"Processando: {common_name} ({chembl_id})")

        # 1. Composto
        compound = fetch_compound(chembl_id)
        if not compound:
            log.warning(f"  Composto {chembl_id} nao encontrado, pulando.")
            continue
        compound_id = upsert_compound(cur, compound)
        log.info(
            f"  Composto: {compound['name']} | "
            f"MW={compound['mol_weight']} | Formula={compound['molecular_formula']}"
        )

        # 2. Bioatividades e alvos
        activities       = fetch_bioactivities(chembl_id)
        targets_inserted = set()
        for act in activities:
            t_chembl = act.get("target_chembl_id")
            if not t_chembl or t_chembl in targets_inserted:
                continue
            targets_inserted.add(t_chembl)
            target = fetch_target(t_chembl)
            if target:
                target_id = upsert_target(cur, target)
                insert_bioactivity(cur, compound_id, target_id, act)
                log.info(
                    f"  Bioatividade: {act.get('type')} = "
                    f"{act.get('value')} {act.get('units')} "
                    f"-> {target['name']} ({target['organism']})"
                )
            time.sleep(0.2)

        # 3. Artigos do PubMed (sem abstract)
        pmids    = search_pubmed(common_name)
        articles = fetch_articles(pmids)
        for article in articles:
            article_id = upsert_article(cur, article)
            link_article_compound(cur, article_id, compound_id)
            title_preview = (article["title"] or "")[:65]
            log.info(f"  Artigo [{article['pmid']}]: {title_preview}...")

        conn.commit()
        log.info(f"  OK - {common_name} salvo.")
        time.sleep(0.5)

    cur.close()
    conn.close()
    log.info("=" * 55)
    log.info("Populacao concluida com sucesso!")


if __name__ == "__main__":
    main()