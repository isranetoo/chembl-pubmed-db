"""
populate.py
-----------
Popula o banco local com compostos populares do ChEMBL
e artigos relacionados do PubMed (abstract completo via efetch XML).

Uso:
    pip install -r requirements.txt
    python populate.py
"""

import json
import logging
import time
import xml.etree.ElementTree as ET
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
    # ── Analgésicos / Anti-inflamatórios ──────────────────────
    ("CHEMBL25",    "Aspirin"),        # NSAID / antiagregante plaquetário
    ("CHEMBL521",   "Ibuprofen"),      # NSAID
    ("CHEMBL112",   "Paracetamol"),    # analgésico / antitérmico
    ("CHEMBL154",   "Naproxen"),       # NSAID

    # ── Sistema Nervoso Central ────────────────────────────────
    ("CHEMBL113",   "Caffeine"),       # estimulante
    ("CHEMBL12",    "Diazepam"),       # benzodiazepínico
    ("CHEMBL70",    "Morphine"),       # opioide
    ("CHEMBL41",    "Fluoxetine"),     # antidepressivo SSRI
    ("CHEMBL809",   "Sertraline"),     # antidepressivo SSRI

    # ── Cardiovascular ────────────────────────────────────────
    ("CHEMBL1464",  "Warfarin"),       # anticoagulante
    ("CHEMBL1491",  "Amlodipine"),     # bloqueador de canal de cálcio
    ("CHEMBL1237",  "Lisinopril"),     # inibidor da ECA
    ("CHEMBL191",   "Losartan"),       # antagonista do receptor de angiotensina II
    ("CHEMBL1064",  "Simvastatin"),    # estatina (HMG-CoA reductase)
    ("CHEMBL1487",  "Atorvastatin"),   # estatina (HMG-CoA reductase)
    ("CHEMBL192",   "Sildenafil"),     # inibidor PDE5

    # ── Metabólico / Endócrino ────────────────────────────────
    ("CHEMBL1431",  "Metformin"),      # antidiabético
    ("CHEMBL384467","Dexamethasone"),  # corticosteroide

    # ── Gastrointestinal ──────────────────────────────────────
    ("CHEMBL1503",  "Omeprazole"),     # inibidor de bomba de prótons

    # ── Antimicrobianos / Antivirais ──────────────────────────
    ("CHEMBL1082",  "Amoxicillin"),    # antibiótico betalactâmico
    ("CHEMBL8",     "Ciprofloxacin"),  # antibiótico fluoroquinolona
    ("CHEMBL1229",  "Oseltamivir"),    # antiviral (inibidor de neuraminidase)

    # ── Oncologia ─────────────────────────────────────────────
    ("CHEMBL83",    "Tamoxifen"),      # antagonista de receptor de estrogênio
    ("CHEMBL941",   "Imatinib"),       # inibidor de tirosina quinase (BCR-ABL)
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

        compound = {
            # ── identidade ──────────────────────────────────
            "chembl_id":         chembl_id,
            "name":              data.get("pref_name") or chembl_id,
            "molecular_formula": props.get("full_molformula"),
            "mol_weight":        props.get("full_mwt"),
            "smiles":            structs.get("canonical_smiles"),
            "inchi_key":         structs.get("standard_inchi_key"),
            # ── propriedades base (mantidas em compounds) ────
            "alogp":             props.get("alogp"),
            "hbd":               props.get("hbd"),
            "hba":               props.get("hba"),
            "psa":               props.get("psa"),
            "ro5_violations":    props.get("num_ro5_violations"),
        }

        # ── propriedades ADMET completas (para admet_properties) ──
        compound["admet"] = {
            "alogp":              props.get("alogp"),
            "cx_logp":            props.get("cx_logp"),
            "cx_logd":            props.get("cx_logd"),
            "cx_most_apka":       props.get("cx_most_apka"),
            "cx_most_bpka":       props.get("cx_most_bpka"),
            "molecular_species":  props.get("molecular_species"),
            "mw_freebase":        props.get("mw_freebase"),
            "mw_monoisotopic":    props.get("mw_monoisotopic"),
            "heavy_atoms":        props.get("heavy_atoms"),
            "aromatic_rings":     props.get("aromatic_rings"),
            "rtb":                props.get("rtb"),
            "hbd":                props.get("hbd"),
            "hbd_lipinski":       props.get("hbd_lipinski"),
            "hba":                props.get("hba"),
            "hba_lipinski":       props.get("hba_lipinski"),
            "psa":                props.get("psa"),
            "num_ro5_violations": props.get("num_ro5_violations"),
            "ro3_pass":           props.get("ro3_pass"),
            "qed_weighted":       props.get("qed_weighted"),
            "num_alerts":         props.get("num_alerts"),
        }

        return compound
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


def _to_numeric(value) -> Optional[float]:
    """Converte string ou numero para float, retorna None se falhar."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def fetch_indications(chembl_id: str) -> list:
    """
    Busca indicações terapêuticas de um composto via ChEMBL drug_indication.

    Cada entrada tem:
      drugind_id       — ID único da indicação no ChEMBL
      mesh_id / mesh_heading — doença pelo vocabulário MeSH
      efo_id  / efo_term     — doença pelo vocabulário EFO
      max_phase_for_ind      — fase clínica máxima (4 = aprovado)

    Endpoint: /drug_indication?molecule_chembl_id={id}
    """
    indications = []
    offset      = 0
    limit       = 100

    while True:
        try:
            r = requests.get(
                f"{CHEMBL_BASE}/drug_indication.json",
                params={
                    "molecule_chembl_id": chembl_id,
                    "limit":  limit,
                    "offset": offset,
                },
                timeout=20,
            )
            r.raise_for_status()
            data  = r.json()
            batch = data.get("drug_indications", [])
            indications.extend(batch)

            total = data.get("page_meta", {}).get("total_count", 0)
            offset += limit
            if offset >= total:
                break

            time.sleep(0.2)

        except Exception as exc:
            log.error(f"Erro ao buscar indicacoes de {chembl_id}: {exc}")
            break

    return indications


# ============================================================
# PubMed — busca de IDs
# ============================================================

def fetch_mechanisms(chembl_id: str) -> list:
    """
    Busca mecanismos de ação via ChEMBL /mechanism.

    Campos relevantes por entrada:
      mec_id              — ID único do mecanismo no ChEMBL
      mechanism_of_action — descrição textual (ex: "Cyclooxygenase inhibitor")
      action_type         — INHIBITOR, AGONIST, ANTAGONIST, BLOCKER, ...
      target_chembl_id    — alvo biológico associado
      target_name         — nome do alvo (desnormalizado)
      direct_interaction  — True se interage diretamente com o alvo
      disease_efficacy    — True se relevante para a eficácia terapêutica
      mechanism_comment   — comentário livre sobre o mecanismo
      selectivity_comment — comentário sobre seletividade
      binding_site_comment— comentário sobre sítio de ligação
    """
    try:
        r = requests.get(
            f"{CHEMBL_BASE}/mechanism.json",
            params={"molecule_chembl_id": chembl_id, "limit": 100},
            timeout=20,
        )
        r.raise_for_status()
        return r.json().get("mechanisms", [])
    except Exception as exc:
        log.error(f"Erro ao buscar mecanismos de {chembl_id}: {exc}")
        return []


def search_pubmed(compound_name: str) -> list:
    """Retorna lista de PMIDs usando esearch (so IDs, sem metadados)."""
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


# ============================================================
# PubMed — helpers de parsing XML
# ============================================================

def _parse_abstract(article_elem: ET.Element) -> Optional[str]:
    """
    Extrai o abstract de <Article>.

    Formatos suportados:
      Simples      -> <AbstractText>Texto corrido...</AbstractText>
      Estruturado  -> <AbstractText Label="BACKGROUND">...</AbstractText>
                      <AbstractText Label="METHODS">...</AbstractText>
                      ...

    itertext() captura texto mesmo com tags inline <b>, <i>, <sub>, <sup>.
    Secoes "UNLABELLED" sao tratadas como texto simples.
    """
    abstract_el = article_elem.find("Abstract")
    if abstract_el is None:
        return None

    sections = []
    for at in abstract_el.findall("AbstractText"):
        text = "".join(at.itertext()).strip()
        if not text:
            continue
        label = at.get("Label") or at.get("NlmCategory", "")
        if label and label.upper() not in ("UNLABELLED", ""):
            sections.append(f"{label.capitalize()}: {text}")
        else:
            sections.append(text)

    if not sections:
        return None
    return "\n\n".join(sections) if len(sections) > 1 else sections[0]


def _parse_year(article_elem: ET.Element) -> Optional[int]:
    """
    Extrai o ano de <PubDate>.
    Lida com <Year>2023</Year> e <MedlineDate>2023 Jan-Feb</MedlineDate>.
    """
    pub_date = article_elem.find(".//PubDate")
    if pub_date is None:
        return None
    year_text = pub_date.findtext("Year")
    if year_text:
        try:
            return int(year_text)
        except ValueError:
            pass
    medline = pub_date.findtext("MedlineDate", "")
    try:
        return int(medline.split()[0])
    except (ValueError, IndexError):
        return None


def _parse_doi(pubmed_article: ET.Element) -> Optional[str]:
    """
    Procura o DOI em dois lugares:
      1. <ELocationID EIdType="doi"> dentro de <Article>
      2. <ArticleId IdType="doi">    dentro de <PubmedData>
    """
    for eid in pubmed_article.findall(".//ELocationID"):
        if eid.get("EIdType", "").lower() == "doi":
            return (eid.text or "").strip() or None
    for aid in pubmed_article.findall(".//ArticleId"):
        if aid.get("IdType", "").lower() == "doi":
            return (aid.text or "").strip() or None
    return None


def _parse_mesh_terms(medline_elem: ET.Element) -> Optional[list]:
    """
    Extrai termos MeSH de <MeshHeadingList>.

    Retorna lista de dicts: {"term": str, "major": bool}
    major=True indica topico principal do artigo.

    Exemplo de query no banco:
      SELECT title
      FROM articles
      WHERE mesh_terms @> '[{"term": "Anti-Inflammatory Agents"}]';
    """
    terms = []
    for heading in medline_elem.findall(".//MeshHeading"):
        descriptor = heading.find("DescriptorName")
        if descriptor is not None and descriptor.text:
            terms.append({
                "term":  descriptor.text.strip(),
                "major": descriptor.get("MajorTopicYN", "N") == "Y",
            })
    return terms if terms else None


def _parse_keywords(medline_elem: ET.Element) -> Optional[list]:
    """
    Extrai palavras-chave dos autores de <KeywordList>.

    Exemplo de query no banco:
      SELECT title FROM articles WHERE keywords @> '["inflammation"]';
    """
    kws = [
        kw.text.strip()
        for kw in medline_elem.findall(".//Keyword")
        if kw.text
    ]
    return kws if kws else None


def _parse_pub_types(article_elem: ET.Element) -> Optional[list]:
    """
    Extrai tipos de publicacao de <PublicationTypeList>.
    Ex: ["Journal Article", "Review", "Clinical Trial", "Meta-Analysis"]
    """
    types = [
        pt.text.strip()
        for pt in article_elem.findall(".//PublicationType")
        if pt.text
    ]
    return types if types else None


# ============================================================
# PubMed — fetch principal
# ============================================================

def fetch_articles(pmids: list) -> list:
    """
    Busca artigos completos via efetch (XML), extraindo:
      - titulo, abstract (simples ou estruturado)
      - autores, periodico, ano, DOI
      - termos MeSH, palavras-chave, tipos de publicacao

    O esearch (usado antes) so retorna IDs.
    O esummary nao retorna abstract.
    O efetch retorna o XML completo — unica forma de ter o abstract.
    """
    if not pmids:
        return []

    try:
        r = requests.get(
            f"{PUBMED_BASE}/efetch.fcgi",
            params={
                "db":      "pubmed",
                "id":      ",".join(pmids),
                "retmode": "xml",
                "rettype": "abstract",
            },
            timeout=30,
        )
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except ET.ParseError as exc:
        log.error(f"Erro ao parsear XML do PubMed: {exc}")
        return []
    except Exception as exc:
        log.error(f"Erro na requisicao efetch: {exc}")
        return []

    articles = []

    for pub_article in root.findall(".//PubmedArticle"):
        try:
            medline    = pub_article.find("MedlineCitation")
            article_el = medline.find("Article")

            pmid = medline.findtext("PMID")
            if not pmid:
                continue

            # Titulo (itertext captura tags inline como <i>, <b>)
            title_el = article_el.find("ArticleTitle")
            title = "".join(title_el.itertext()).strip() if title_el is not None else None

            # Autores
            authors = []
            author_list = article_el.find("AuthorList")
            if author_list is not None:
                for author in author_list.findall("Author"):
                    collective = author.findtext("CollectiveName")
                    if collective:
                        authors.append(collective.strip())
                    else:
                        last = author.findtext("LastName", "")
                        fore = author.findtext("ForeName", "")
                        name = f"{fore} {last}".strip()
                        if name:
                            authors.append(name)

            # Periodico
            journal    = None
            journal_el = article_el.find("Journal")
            if journal_el is not None:
                journal = (
                    journal_el.findtext("Title")
                    or journal_el.findtext("ISOAbbreviation")
                )

            articles.append({
                "pmid":       pmid,
                "title":      title,
                "abstract":   _parse_abstract(article_el),
                "authors":    json.dumps(authors),
                "journal":    journal,
                "pub_year":   _parse_year(article_el),
                "doi":        _parse_doi(pub_article),
                "mesh_terms": json.dumps(_parse_mesh_terms(medline)),
                "keywords":   json.dumps(_parse_keywords(medline)),
                "pub_types":  json.dumps(_parse_pub_types(article_el)),
            })

        except Exception as exc:
            log.warning(f"  Artigo ignorado por erro de parsing: {exc}")
            continue

    with_abstract = sum(1 for a in articles if a["abstract"])
    log.info(
        f"  efetch: {len(articles)}/{len(pmids)} artigos parseados | "
        f"{with_abstract} com abstract"
    )
    return articles


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


def upsert_indication(cur, compound_id: str, ind: dict):
    """
    Insere ou atualiza uma indicacao terapeutica.

    ON CONFLICT em drugind_id (PK do ChEMBL):
      - max_phase usa GREATEST para nunca regredir a fase clinica
      - demais campos usam COALESCE para nao sobrescrever com NULL
    """
    cur.execute(
        """
        INSERT INTO indications
            (drugind_id, compound_id, mesh_id, mesh_heading,
             efo_id, efo_term, max_phase)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (drugind_id) DO UPDATE SET
            max_phase    = GREATEST(EXCLUDED.max_phase,    indications.max_phase),
            mesh_heading = COALESCE(EXCLUDED.mesh_heading, indications.mesh_heading),
            efo_id       = COALESCE(EXCLUDED.efo_id,       indications.efo_id),
            efo_term     = COALESCE(EXCLUDED.efo_term,     indications.efo_term)
        """,
        (
            ind.get("drugind_id"),
            compound_id,
            ind.get("mesh_id"),
            ind.get("mesh_heading"),
            ind.get("efo_id"),
            ind.get("efo_term"),
            _to_numeric(ind.get("max_phase_for_ind")),
        ),
    )


def upsert_mechanism(cur, compound_id: str, mec: dict, target_id: Optional[str]):
    """
    Insere ou atualiza um mecanismo de ação.

    ON CONFLICT em mec_id (PK do ChEMBL):
      - campos texto usam COALESCE para não sobrescrever com NULL
      - target_id é atualizado quando encontrado na tabela targets
    """
    cur.execute(
        """
        INSERT INTO mechanisms (
            mec_id, compound_id, target_id, target_chembl_id, target_name,
            mechanism_of_action, action_type,
            direct_interaction, disease_efficacy,
            mechanism_comment, selectivity_comment, binding_site_comment
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (mec_id) DO UPDATE SET
            target_id           = COALESCE(EXCLUDED.target_id,            mechanisms.target_id),
            mechanism_of_action = COALESCE(EXCLUDED.mechanism_of_action,  mechanisms.mechanism_of_action),
            action_type         = COALESCE(EXCLUDED.action_type,          mechanisms.action_type),
            mechanism_comment   = COALESCE(EXCLUDED.mechanism_comment,    mechanisms.mechanism_comment),
            selectivity_comment = COALESCE(EXCLUDED.selectivity_comment,  mechanisms.selectivity_comment),
            binding_site_comment= COALESCE(EXCLUDED.binding_site_comment, mechanisms.binding_site_comment)
        """,
        (
            mec.get("mec_id"),
            compound_id,
            target_id,
            mec.get("target_chembl_id"),
            mec.get("target_name"),
            mec.get("mechanism_of_action"),
            mec.get("action_type"),
            bool(mec.get("direct_interaction")),
            bool(mec.get("disease_efficacy")),
            mec.get("mechanism_comment"),
            mec.get("selectivity_comment"),
            mec.get("binding_site_comment"),
        ),
    )


def upsert_admet(cur, compound_id: str, admet: dict):
    """
    Insere ou atualiza as propriedades ADMET de um composto.
    ON CONFLICT em compound_id — cada composto tem exatamente uma linha.
    COALESCE garante que valores existentes não sejam sobrescritos por NULL.
    """
    cur.execute(
        """
        INSERT INTO admet_properties (
            compound_id,
            alogp, cx_logp, cx_logd,
            cx_most_apka, cx_most_bpka, molecular_species,
            mw_freebase, mw_monoisotopic, heavy_atoms, aromatic_rings, rtb,
            hbd, hbd_lipinski, hba, hba_lipinski, psa,
            num_ro5_violations, ro3_pass, qed_weighted, num_alerts
        ) VALUES (
            %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s
        )
        ON CONFLICT (compound_id) DO UPDATE SET
            alogp              = COALESCE(EXCLUDED.alogp,              admet_properties.alogp),
            cx_logp            = COALESCE(EXCLUDED.cx_logp,            admet_properties.cx_logp),
            cx_logd            = COALESCE(EXCLUDED.cx_logd,            admet_properties.cx_logd),
            cx_most_apka       = COALESCE(EXCLUDED.cx_most_apka,       admet_properties.cx_most_apka),
            cx_most_bpka       = COALESCE(EXCLUDED.cx_most_bpka,       admet_properties.cx_most_bpka),
            molecular_species  = COALESCE(EXCLUDED.molecular_species,  admet_properties.molecular_species),
            mw_freebase        = COALESCE(EXCLUDED.mw_freebase,        admet_properties.mw_freebase),
            mw_monoisotopic    = COALESCE(EXCLUDED.mw_monoisotopic,    admet_properties.mw_monoisotopic),
            heavy_atoms        = COALESCE(EXCLUDED.heavy_atoms,        admet_properties.heavy_atoms),
            aromatic_rings     = COALESCE(EXCLUDED.aromatic_rings,     admet_properties.aromatic_rings),
            rtb                = COALESCE(EXCLUDED.rtb,                admet_properties.rtb),
            hbd                = COALESCE(EXCLUDED.hbd,                admet_properties.hbd),
            hbd_lipinski       = COALESCE(EXCLUDED.hbd_lipinski,       admet_properties.hbd_lipinski),
            hba                = COALESCE(EXCLUDED.hba,                admet_properties.hba),
            hba_lipinski       = COALESCE(EXCLUDED.hba_lipinski,       admet_properties.hba_lipinski),
            psa                = COALESCE(EXCLUDED.psa,                admet_properties.psa),
            num_ro5_violations = COALESCE(EXCLUDED.num_ro5_violations, admet_properties.num_ro5_violations),
            ro3_pass           = COALESCE(EXCLUDED.ro3_pass,           admet_properties.ro3_pass),
            qed_weighted       = COALESCE(EXCLUDED.qed_weighted,       admet_properties.qed_weighted),
            num_alerts         = COALESCE(EXCLUDED.num_alerts,         admet_properties.num_alerts)
        """,
        (
            compound_id,
            _to_numeric(admet.get("alogp")),
            _to_numeric(admet.get("cx_logp")),
            _to_numeric(admet.get("cx_logd")),
            _to_numeric(admet.get("cx_most_apka")),
            _to_numeric(admet.get("cx_most_bpka")),
            admet.get("molecular_species"),
            _to_numeric(admet.get("mw_freebase")),
            _to_numeric(admet.get("mw_monoisotopic")),
            admet.get("heavy_atoms"),
            admet.get("aromatic_rings"),
            admet.get("rtb"),
            admet.get("hbd"),
            admet.get("hbd_lipinski"),
            admet.get("hba"),
            admet.get("hba_lipinski"),
            _to_numeric(admet.get("psa")),
            admet.get("num_ro5_violations"),
            admet.get("ro3_pass"),
            _to_numeric(admet.get("qed_weighted")),
            admet.get("num_alerts"),
        ),
    )


def upsert_article(cur, data: dict) -> str:
    """
    Insere ou atualiza um artigo.
    COALESCE garante que campos preenchidos nao sejam sobrescritos
    por NULL em re-execucoes parciais.
    """
    cur.execute(
        """
        INSERT INTO articles
            (pmid, title, abstract, authors, journal, pub_year, doi,
             mesh_terms, keywords, pub_types)
        VALUES
            (%(pmid)s, %(title)s, %(abstract)s, %(authors)s::jsonb,
             %(journal)s, %(pub_year)s, %(doi)s,
             %(mesh_terms)s::jsonb, %(keywords)s::jsonb, %(pub_types)s::jsonb)
        ON CONFLICT (pmid) DO UPDATE SET
            title      = COALESCE(EXCLUDED.title,      articles.title),
            abstract   = COALESCE(EXCLUDED.abstract,   articles.abstract),
            doi        = COALESCE(EXCLUDED.doi,        articles.doi),
            mesh_terms = COALESCE(EXCLUDED.mesh_terms, articles.mesh_terms),
            keywords   = COALESCE(EXCLUDED.keywords,   articles.keywords),
            pub_types  = COALESCE(EXCLUDED.pub_types,  articles.pub_types)
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

        # 2. Propriedades ADMET (sem requisição extra — vêm do fetch_compound)
        admet = compound.get("admet", {})
        upsert_admet(cur, compound_id, admet)
        log.info(
            f"  ADMET: QED={admet.get('qed_weighted') or '?'} | "
            f"aLogP={admet.get('alogp') or '?'} | "
            f"PSA={admet.get('psa') or '?'} | "
            f"Ro5={admet.get('num_ro5_violations') or 0} violacoes"
        )

        # 3. Bioatividades e alvos
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

        # 4. Indicações terapêuticas (doenças que o composto trata)
        indications = fetch_indications(chembl_id)
        approved    = 0
        for ind in indications:
            upsert_indication(cur, compound_id, ind)
            if (_to_numeric(ind.get("max_phase_for_ind")) or 0) >= 4:
                approved += 1
        if indications:
            log.info(
                f"  Indicacoes: {len(indications)} total | "
                f"{approved} aprovadas | "
                f"ex: {indications[0].get('mesh_heading') or indications[0].get('efo_term')}"
            )

        # 5. Mecanismos de ação
        mechanisms = fetch_mechanisms(chembl_id)
        for mec in mechanisms:
            # tenta linkar ao target já inserido no banco
            t_chembl  = mec.get("target_chembl_id")
            target_id = None
            if t_chembl:
                cur.execute(
                    "SELECT id FROM targets WHERE chembl_id = %s", (t_chembl,)
                )
                row = cur.fetchone()
                if row:
                    target_id = row[0]
            upsert_mechanism(cur, compound_id, mec, target_id)
        if mechanisms:
            action_types = list({m.get("action_type") for m in mechanisms if m.get("action_type")})
            log.info(
                f"  Mecanismos: {len(mechanisms)} | "
                f"tipos: {', '.join(sorted(action_types)) or '?'}"
            )

        # 6. Artigos do PubMed com abstract completo (efetch XML)
        pmids    = search_pubmed(common_name)
        articles = fetch_articles(pmids)

        for article in articles:
            article_id = upsert_article(cur, article)
            link_article_compound(cur, article_id, compound_id)

            has_abstract = "abstract OK" if article["abstract"] else "sem abstract"
            n_mesh       = len(json.loads(article["mesh_terms"] or "[]") or [])
            n_kw         = len(json.loads(article["keywords"]   or "[]") or [])
            pub_types    = json.loads(article["pub_types"] or "[]") or []
            tipo         = pub_types[0] if pub_types else "?"

            log.info(
                f"  [{article['pmid']}] {has_abstract} | "
                f"{n_mesh} MeSH | {n_kw} keywords | {tipo}"
            )
            log.info(f"    {(article['title'] or '')[:72]}...")
            if article["abstract"]:
                log.info(f"    {article['abstract'][:100]}...")

        conn.commit()
        log.info(f"  OK - {common_name} salvo.")
        time.sleep(0.5)

    cur.close()
    conn.close()
    log.info("=" * 55)
    log.info("Populacao concluida com sucesso!")


if __name__ == "__main__":
    main()