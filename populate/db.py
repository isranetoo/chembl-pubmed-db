"""
db.py
-----
Funções de persistência no banco PostgreSQL.
Todas usam ON CONFLICT para permitir re-execuções idempotentes.

Convenções:
  upsert_*  — INSERT ... ON CONFLICT DO UPDATE
  insert_*  — INSERT simples (sem constraint de unicidade)
  link_*    — tabelas de junção N:M
"""

import logging
from typing import Optional

from chembl_client import to_numeric
from config import DB_CONFIG

log = logging.getLogger(__name__)

# Logar destino do banco na inicialização do módulo
_host = DB_CONFIG.get("host", "?")
_db   = DB_CONFIG.get("dbname", "?")
_ssl  = DB_CONFIG.get("sslmode", "off")
log.info(f"Banco de dados: {_host}/{_db} (ssl={_ssl})")


# ============================================================
# Status incremental
# ============================================================

def get_compound_status(cur, chembl_id: str) -> Optional[dict]:
    """
    Consulta o banco para saber o que já está populado para um chembl_id.

    Retorna None se o composto ainda não existe.
    Retorna um dict com:
      id           — UUID do composto no banco
      has_admet    — True se admet_properties tem linha para este composto
      has_bioact   — True se bioactivities tem ao menos 1 linha
      has_ind      — True se indications tem ao menos 1 linha
      has_mec      — True se mechanisms tem ao menos 1 linha
      has_articles — True se article_compounds tem ao menos 1 linha
      is_complete  — True se todas as 5 etapas estão preenchidas

    Usado em populate.py para decidir quais etapas pular.
    """
    cur.execute(
        """
        SELECT
            c.id,
            EXISTS (SELECT 1 FROM admet_properties ap
                    WHERE ap.compound_id = c.id)              AS has_admet,
            EXISTS (SELECT 1 FROM bioactivities    b
                    WHERE b.compound_id  = c.id)              AS has_bioact,
            EXISTS (SELECT 1 FROM indications      i
                    WHERE i.compound_id  = c.id)              AS has_ind,
            EXISTS (SELECT 1 FROM mechanisms       m
                    WHERE m.compound_id  = c.id)              AS has_mec,
            EXISTS (SELECT 1 FROM article_compounds ac
                    WHERE ac.compound_id = c.id)              AS has_articles
        FROM compounds c
        WHERE c.chembl_id = %s
        """,
        (chembl_id,),
    )
    row = cur.fetchone()
    if not row:
        return None

    status = {
        "id":           row[0],
        "has_admet":    row[1],
        "has_bioact":   row[2],
        "has_ind":      row[3],
        "has_mec":      row[4],
        "has_articles": row[5],
    }
    status["is_complete"] = all([
        status["has_admet"],
        status["has_bioact"],
        status["has_ind"],
        status["has_mec"],
        status["has_articles"],
    ])
    return status

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


# ============================================================
# Alvos e bioatividades
# ============================================================

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


# ============================================================
# Indicações terapêuticas
# ============================================================

def upsert_indication(cur, compound_id: str, ind: dict):
    """
    ON CONFLICT em drugind_id (PK do ChEMBL):
      - max_phase usa GREATEST para nunca regredir a fase clínica
      - demais campos usam COALESCE para não sobrescrever com NULL
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
            to_numeric(ind.get("max_phase_for_ind")),
        ),
    )


# ============================================================
# Mecanismos de ação
# ============================================================

def upsert_mechanism(cur, compound_id: str, mec: dict, target_id: Optional[str]):
    """
    ON CONFLICT em mec_id (PK do ChEMBL):
      - campos texto usam COALESCE para não sobrescrever com NULL
      - target_id é atualizado quando o alvo for encontrado na tabela targets
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
            target_id            = COALESCE(EXCLUDED.target_id,            mechanisms.target_id),
            mechanism_of_action  = COALESCE(EXCLUDED.mechanism_of_action,  mechanisms.mechanism_of_action),
            action_type          = COALESCE(EXCLUDED.action_type,          mechanisms.action_type),
            mechanism_comment    = COALESCE(EXCLUDED.mechanism_comment,    mechanisms.mechanism_comment),
            selectivity_comment  = COALESCE(EXCLUDED.selectivity_comment,  mechanisms.selectivity_comment),
            binding_site_comment = COALESCE(EXCLUDED.binding_site_comment, mechanisms.binding_site_comment)
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


# ============================================================
# Propriedades ADMET
# ============================================================

def upsert_admet(cur, compound_id: str, admet: dict):
    """
    ON CONFLICT em compound_id — cada composto tem exatamente uma linha.
    COALESCE garante que valores existentes não sejam sobrescritos por NULL
    em re-execuções parciais.
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
            to_numeric(admet.get("alogp")),
            to_numeric(admet.get("cx_logp")),
            to_numeric(admet.get("cx_logd")),
            to_numeric(admet.get("cx_most_apka")),
            to_numeric(admet.get("cx_most_bpka")),
            admet.get("molecular_species"),
            to_numeric(admet.get("mw_freebase")),
            to_numeric(admet.get("mw_monoisotopic")),
            admet.get("heavy_atoms"),
            admet.get("aromatic_rings"),
            admet.get("rtb"),
            admet.get("hbd"),
            admet.get("hbd_lipinski"),
            admet.get("hba"),
            admet.get("hba_lipinski"),
            to_numeric(admet.get("psa")),
            admet.get("num_ro5_violations"),
            admet.get("ro3_pass"),
            to_numeric(admet.get("qed_weighted")),
            admet.get("num_alerts"),
        ),
    )


# ============================================================
# Artigos
# ============================================================

def upsert_article(cur, data: dict) -> str:
    """
    COALESCE garante que campos já preenchidos não sejam sobrescritos
    por NULL em re-execuções parciais.
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