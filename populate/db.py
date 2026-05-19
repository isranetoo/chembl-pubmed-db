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

import json
import logging
from typing import Optional

import psycopg2

from .chembl_client import to_numeric
from .config import DB_CONFIG


def get_conn():
    """Return a new psycopg2 connection using DB_CONFIG."""
    return psycopg2.connect(**DB_CONFIG)


def load_popular_compounds() -> list:
    """
    Lê a lista de compostos seed da tabela `seed_compounds` (apenas is_active).

    Retorna lista de tuplas (chembl_id, common_name) — mesma forma da antiga
    constante `POPULAR_COMPOUNDS` em populate/config.py, para que o
    `populate.py` continue funcionando sem mudanças além do import.

    Levanta `RuntimeError` se a tabela ainda não foi criada, apontando para
    a migration Alembic responsável (0002_seed_compounds).
    """
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT chembl_id, common_name "
                "FROM seed_compounds "
                "WHERE is_active = TRUE "
                "ORDER BY category, common_name"
            )
            return [(r[0], r[1]) for r in cur.fetchall()]
    except psycopg2.errors.UndefinedTable as exc:
        raise RuntimeError(
            "Tabela `seed_compounds` não existe no banco. "
            "Aplique a migration: `alembic upgrade head` "
            "(ela cria a tabela e popula com a lista padrão de 51 compostos)."
        ) from exc


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
      id            — UUID do composto no banco
      has_metadata  — True se o metadata clínico/regulatório (migration 0004)
                      já foi preenchido. Usa molecule_type como sentinela
                      porque o ChEMBL praticamente sempre retorna esse campo.
      has_admet     — True se admet_properties tem linha para este composto
      has_bioact          — True se bioactivities tem ao menos 1 linha
      has_bioact_enriched — True se há bioatividade com assay_type não-NULL
                            (sentinela da migration 0005 — bioatividades
                             antigas têm assay_type NULL e precisam ser
                             re-fetched com os campos enriquecidos)
      has_ind       — True se indications tem ao menos 1 linha
      has_mec       — True se mechanisms tem ao menos 1 linha
      has_articles  — True se article_compounds tem ao menos 1 linha
      has_trials    — True se compound_clinical_trials tem ao menos 1 link
                      pro chembl_id (sentinela: composto já foi sincronizado
                      com a CT.gov pelo menos uma vez)
      has_target_enriched
                    — True se TODOS os alvos referenciados pelo composto
                      (via bioactivities OU mechanisms) têm tax_id preenchido.
                      Sentinela da migration 0006. Quando False, há alvo
                      faltando enrichment (components + xrefs).
      is_complete   — True se todas as 9 etapas estão preenchidas

    Usado em populate.py para decidir quais etapas pular.
    """
    cur.execute(
        """
        SELECT
            c.id,
            (c.molecule_type IS NOT NULL)                     AS has_metadata,
            EXISTS (SELECT 1 FROM admet_properties ap
                    WHERE ap.compound_id = c.id)              AS has_admet,
            EXISTS (SELECT 1 FROM bioactivities    b
                    WHERE b.compound_id  = c.id)              AS has_bioact,
            EXISTS (SELECT 1 FROM bioactivities    b
                    WHERE b.compound_id  = c.id
                      AND b.assay_type   IS NOT NULL)         AS has_bioact_enriched,
            EXISTS (SELECT 1 FROM indications      i
                    WHERE i.compound_id  = c.id)              AS has_ind,
            EXISTS (SELECT 1 FROM mechanisms       m
                    WHERE m.compound_id  = c.id)              AS has_mec,
            EXISTS (SELECT 1 FROM article_compounds ac
                    WHERE ac.compound_id = c.id)              AS has_articles,
            EXISTS (SELECT 1 FROM compound_clinical_trials cct
                    WHERE cct.chembl_id  = c.chembl_id)       AS has_trials,
            -- has_target_enriched = "nenhum target usado pelo composto está
            -- sem tax_id". É TRUE também quando o composto ainda não tem
            -- nenhum target (vazio satisfaz universalmente).
            NOT EXISTS (
                SELECT 1
                FROM (
                    SELECT target_id FROM bioactivities
                    WHERE compound_id = c.id AND target_id IS NOT NULL
                    UNION
                    SELECT target_id FROM mechanisms
                    WHERE compound_id = c.id AND target_id IS NOT NULL
                ) used
                JOIN targets t ON t.id = used.target_id
                WHERE t.tax_id IS NULL
            )                                                 AS has_target_enriched
        FROM compounds c
        WHERE c.chembl_id = %s
        """,
        (chembl_id,),
    )
    row = cur.fetchone()
    if not row:
        return None

    status = {
        "id":                   row[0],
        "has_metadata":         row[1],
        "has_admet":            row[2],
        "has_bioact":           row[3],
        "has_bioact_enriched":  row[4],
        "has_ind":              row[5],
        "has_mec":              row[6],
        "has_articles":         row[7],
        "has_trials":           row[8],
        "has_target_enriched":  row[9],
    }
    # `has_bioact_enriched` implica `has_bioact`. Pedimos o "enriched" no
    # is_complete para que compostos com bioatividades legadas (sem
    # assay_type) sejam marcados como [PARCIAL] e re-fetched.
    status["is_complete"] = all([
        status["has_metadata"],
        status["has_admet"],
        status["has_bioact_enriched"],
        status["has_ind"],
        status["has_mec"],
        status["has_articles"],
        status["has_trials"],
        status["has_target_enriched"],
    ])
    return status

def upsert_compound(cur, data: dict) -> str:
    """
    Upsert por chembl_id. ON CONFLICT atualiza `name` e usa COALESCE para
    todos os outros campos — re-execuções parciais não sobrescrevem dados
    já preenchidos com NULL.
    """
    cur.execute(
        """
        INSERT INTO compounds (
            chembl_id, name, molecular_formula, mol_weight, smiles,
            inchi, inchi_key, alogp, hbd, hba, psa, ro5_violations,
            max_phase, first_approval, molecule_type,
            oral, parenteral, topical,
            black_box_warning,
            withdrawn_flag, withdrawn_reason, withdrawn_year,
            withdrawn_country, withdrawn_class,
            prodrug, natural_product, therapeutic_flag,
            first_in_class, orphan,
            chirality, availability_type,
            usan_stem, usan_stem_definition, usan_year,
            np_likeness_score
        )
        VALUES (
            %(chembl_id)s, %(name)s, %(molecular_formula)s, %(mol_weight)s, %(smiles)s,
            %(inchi)s, %(inchi_key)s, %(alogp)s, %(hbd)s, %(hba)s, %(psa)s, %(ro5_violations)s,
            %(max_phase)s, %(first_approval)s, %(molecule_type)s,
            %(oral)s, %(parenteral)s, %(topical)s,
            %(black_box_warning)s,
            %(withdrawn_flag)s, %(withdrawn_reason)s, %(withdrawn_year)s,
            %(withdrawn_country)s, %(withdrawn_class)s,
            %(prodrug)s, %(natural_product)s, %(therapeutic_flag)s,
            %(first_in_class)s, %(orphan)s,
            %(chirality)s, %(availability_type)s,
            %(usan_stem)s, %(usan_stem_definition)s, %(usan_year)s,
            %(np_likeness_score)s
        )
        ON CONFLICT (chembl_id) DO UPDATE SET
            name                 = EXCLUDED.name,
            inchi                = COALESCE(EXCLUDED.inchi,                compounds.inchi),
            max_phase            = GREATEST(EXCLUDED.max_phase,            compounds.max_phase),
            first_approval       = COALESCE(EXCLUDED.first_approval,       compounds.first_approval),
            molecule_type        = COALESCE(EXCLUDED.molecule_type,        compounds.molecule_type),
            oral                 = COALESCE(EXCLUDED.oral,                 compounds.oral),
            parenteral           = COALESCE(EXCLUDED.parenteral,           compounds.parenteral),
            topical              = COALESCE(EXCLUDED.topical,              compounds.topical),
            black_box_warning    = COALESCE(EXCLUDED.black_box_warning,    compounds.black_box_warning),
            withdrawn_flag       = COALESCE(EXCLUDED.withdrawn_flag,       compounds.withdrawn_flag),
            withdrawn_reason     = COALESCE(EXCLUDED.withdrawn_reason,     compounds.withdrawn_reason),
            withdrawn_year       = COALESCE(EXCLUDED.withdrawn_year,       compounds.withdrawn_year),
            withdrawn_country    = COALESCE(EXCLUDED.withdrawn_country,    compounds.withdrawn_country),
            withdrawn_class      = COALESCE(EXCLUDED.withdrawn_class,      compounds.withdrawn_class),
            prodrug              = COALESCE(EXCLUDED.prodrug,              compounds.prodrug),
            natural_product      = COALESCE(EXCLUDED.natural_product,      compounds.natural_product),
            therapeutic_flag     = COALESCE(EXCLUDED.therapeutic_flag,     compounds.therapeutic_flag),
            first_in_class       = COALESCE(EXCLUDED.first_in_class,       compounds.first_in_class),
            orphan               = COALESCE(EXCLUDED.orphan,               compounds.orphan),
            chirality            = COALESCE(EXCLUDED.chirality,            compounds.chirality),
            availability_type    = COALESCE(EXCLUDED.availability_type,    compounds.availability_type),
            usan_stem            = COALESCE(EXCLUDED.usan_stem,            compounds.usan_stem),
            usan_stem_definition = COALESCE(EXCLUDED.usan_stem_definition, compounds.usan_stem_definition),
            usan_year            = COALESCE(EXCLUDED.usan_year,            compounds.usan_year),
            np_likeness_score    = COALESCE(EXCLUDED.np_likeness_score,    compounds.np_likeness_score)
        RETURNING id
        """,
        data,
    )
    return cur.fetchone()[0]


def upsert_compound_synonyms(cur, compound_id: str, synonyms: list) -> int:
    """
    Insere sinônimos do composto (INN, BAN, USAN, trade names, research codes).
    Idempotente: a UNIQUE (compound_id, synonym, syn_type) cobre re-execuções.
    Retorna o número de linhas processadas.
    """
    if not synonyms:
        return 0
    for s in synonyms:
        cur.execute(
            """
            INSERT INTO compound_synonyms (compound_id, synonym, syn_type)
            VALUES (%s, %s, %s)
            ON CONFLICT (compound_id, synonym, syn_type) DO NOTHING
            """,
            (compound_id, s.get("synonym"), s.get("syn_type")),
        )
    return len(synonyms)


def upsert_compound_atc(cur, compound_id: str, atc_list: list) -> int:
    """
    Insere classificações ATC do composto. Idempotente por
    UNIQUE (compound_id, level5).
    """
    if not atc_list:
        return 0
    for atc in atc_list:
        cur.execute(
            """
            INSERT INTO compound_atc (
                compound_id, level5,
                level1, level1_description,
                level2, level2_description,
                level3, level3_description,
                level4, level4_description
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (compound_id, level5) DO UPDATE SET
                level1             = COALESCE(EXCLUDED.level1,             compound_atc.level1),
                level1_description = COALESCE(EXCLUDED.level1_description, compound_atc.level1_description),
                level2             = COALESCE(EXCLUDED.level2,             compound_atc.level2),
                level2_description = COALESCE(EXCLUDED.level2_description, compound_atc.level2_description),
                level3             = COALESCE(EXCLUDED.level3,             compound_atc.level3),
                level3_description = COALESCE(EXCLUDED.level3_description, compound_atc.level3_description),
                level4             = COALESCE(EXCLUDED.level4,             compound_atc.level4),
                level4_description = COALESCE(EXCLUDED.level4_description, compound_atc.level4_description)
            """,
            (
                compound_id,
                atc.get("level5"),
                atc.get("level1"), atc.get("level1_description"),
                atc.get("level2"), atc.get("level2_description"),
                atc.get("level3"), atc.get("level3_description"),
                atc.get("level4"), atc.get("level4_description"),
            ),
        )
    return len(atc_list)


# ============================================================
# Alvos e bioatividades
# ============================================================

def upsert_target(cur, data: dict) -> str:
    """
    Upsert por chembl_id. COALESCE para os campos opcionais — re-execução
    com dados parciais não regride colunas já preenchidas.
    """
    cur.execute(
        """
        INSERT INTO targets (chembl_id, name, type, organism, tax_id, species_group_flag)
        VALUES (%(chembl_id)s, %(name)s, %(type)s, %(organism)s, %(tax_id)s, %(species_group_flag)s)
        ON CONFLICT (chembl_id) DO UPDATE SET
            name               = EXCLUDED.name,
            type               = COALESCE(EXCLUDED.type,               targets.type),
            organism           = COALESCE(EXCLUDED.organism,           targets.organism),
            tax_id             = COALESCE(EXCLUDED.tax_id,             targets.tax_id),
            species_group_flag = COALESCE(EXCLUDED.species_group_flag, targets.species_group_flag)
        RETURNING id
        """,
        {
            "chembl_id":          data.get("chembl_id"),
            "name":               data.get("name"),
            "type":               data.get("type"),
            "organism":           data.get("organism"),
            "tax_id":             data.get("tax_id"),
            "species_group_flag": data.get("species_group_flag"),
        },
    )
    return cur.fetchone()[0]


def upsert_target_components(cur, target_id: str, components: list) -> int:
    """
    Insere componentes do alvo e suas xrefs (PDB, GO, UniProt, Reactome…).
    Retorna o número de componentes inseridos/atualizados.

    Idempotente:
      - target_components.UNIQUE (target_id, component_id)
      - target_xrefs.UNIQUE     (component_id, xref_src_db, xref_id)
    """
    if not components:
        return 0
    n = 0
    for comp in components:
        if not comp.get("component_id"):
            continue
        cur.execute(
            """
            INSERT INTO target_components (
                target_id, component_id,
                accession, gene_symbol,
                component_type, component_description, relationship
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (target_id, component_id) DO UPDATE SET
                accession             = COALESCE(EXCLUDED.accession,             target_components.accession),
                gene_symbol           = COALESCE(EXCLUDED.gene_symbol,           target_components.gene_symbol),
                component_type        = COALESCE(EXCLUDED.component_type,        target_components.component_type),
                component_description = COALESCE(EXCLUDED.component_description, target_components.component_description),
                relationship          = COALESCE(EXCLUDED.relationship,          target_components.relationship)
            RETURNING id
            """,
            (
                target_id, comp.get("component_id"),
                comp.get("accession"), comp.get("gene_symbol"),
                comp.get("component_type"), comp.get("component_description"),
                comp.get("relationship"),
            ),
        )
        component_uuid = cur.fetchone()[0]
        upsert_target_xrefs(cur, component_uuid, comp.get("xrefs") or [])
        n += 1
    return n


def upsert_target_xrefs(cur, component_id: str, xrefs: list) -> int:
    """
    Insere cross-references de um componente proteico. Idempotente via
    UNIQUE (component_id, xref_src_db, xref_id).
    """
    if not xrefs:
        return 0
    for x in xrefs:
        cur.execute(
            """
            INSERT INTO target_xrefs (component_id, xref_src_db, xref_id, xref_name)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (component_id, xref_src_db, xref_id) DO UPDATE SET
                xref_name = COALESCE(EXCLUDED.xref_name, target_xrefs.xref_name)
            """,
            (component_id, x.get("xref_src_db"), x.get("xref_id"), x.get("xref_name")),
        )
    return len(xrefs)


def upsert_bioactivity(cur, compound_id: str, target_id: str, act: dict):
    """
    Insere ou atualiza uma bioatividade.

    Idempotência: o índice UNIQUE parcial em `activity_id` (migration 0005)
    permite ON CONFLICT DO UPDATE. Linhas legadas (sem activity_id) ficam
    fora da constraint e podem coexistir — para sobrescrevê-las, use
    `delete_legacy_bioactivities` antes de re-popular.

    `act` deve ser o dict normalizado por `normalize_bioactivity`.
    """
    cur.execute(
        """
        INSERT INTO bioactivities (
            compound_id, target_id, activity_id,
            activity_type, value, units, relation,
            standard_value, standard_units, pchembl_value,
            assay_chembl_id, assay_description, assay_type, bao_label,
            target_organism, target_tax_id,
            document_chembl_id, document_journal, document_year,
            bei, le, lle, sei,
            data_validity_comment, activity_comment, potential_duplicate,
            assay_variant_accession, assay_variant_mutation
        )
        VALUES (
            %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s
        )
        ON CONFLICT (activity_id) WHERE activity_id IS NOT NULL DO UPDATE SET
            pchembl_value         = COALESCE(EXCLUDED.pchembl_value,         bioactivities.pchembl_value),
            standard_value        = COALESCE(EXCLUDED.standard_value,        bioactivities.standard_value),
            standard_units        = COALESCE(EXCLUDED.standard_units,        bioactivities.standard_units),
            assay_description     = COALESCE(EXCLUDED.assay_description,     bioactivities.assay_description),
            assay_type            = COALESCE(EXCLUDED.assay_type,            bioactivities.assay_type),
            bao_label             = COALESCE(EXCLUDED.bao_label,             bioactivities.bao_label),
            target_organism       = COALESCE(EXCLUDED.target_organism,       bioactivities.target_organism),
            target_tax_id         = COALESCE(EXCLUDED.target_tax_id,         bioactivities.target_tax_id),
            document_journal      = COALESCE(EXCLUDED.document_journal,      bioactivities.document_journal),
            document_year         = COALESCE(EXCLUDED.document_year,         bioactivities.document_year),
            bei                   = COALESCE(EXCLUDED.bei,                   bioactivities.bei),
            le                    = COALESCE(EXCLUDED.le,                    bioactivities.le),
            lle                   = COALESCE(EXCLUDED.lle,                   bioactivities.lle),
            sei                   = COALESCE(EXCLUDED.sei,                   bioactivities.sei),
            data_validity_comment = COALESCE(EXCLUDED.data_validity_comment, bioactivities.data_validity_comment),
            activity_comment      = COALESCE(EXCLUDED.activity_comment,      bioactivities.activity_comment),
            potential_duplicate   = COALESCE(EXCLUDED.potential_duplicate,   bioactivities.potential_duplicate),
            assay_variant_mutation  = COALESCE(EXCLUDED.assay_variant_mutation,  bioactivities.assay_variant_mutation),
            assay_variant_accession = COALESCE(EXCLUDED.assay_variant_accession, bioactivities.assay_variant_accession)
        """,
        (
            compound_id, target_id, act.get("activity_id"),
            act.get("type"), act.get("value"), act.get("units"), act.get("relation"),
            act.get("standard_value"), act.get("standard_units"), act.get("pchembl_value"),
            act.get("assay_chembl_id"), act.get("assay_description"), act.get("assay_type"), act.get("bao_label"),
            act.get("target_organism"), act.get("target_tax_id"),
            act.get("document_chembl_id"), act.get("document_journal"), act.get("document_year"),
            act.get("bei"), act.get("le"), act.get("lle"), act.get("sei"),
            act.get("data_validity_comment"), act.get("activity_comment"), act.get("potential_duplicate"),
            act.get("assay_variant_accession"), act.get("assay_variant_mutation"),
        ),
    )


def delete_legacy_bioactivities(cur, compound_id: str) -> int:
    """
    Remove bioatividades legadas (sem assay_type/activity_id) de um composto,
    para permitir re-inserção com os campos enriquecidos da migration 0005.

    Linhas modernas (com assay_type não-NULL) são preservadas — o UPSERT
    cuidará de atualizá-las pelo activity_id.

    Retorna o número de linhas deletadas.
    """
    cur.execute(
        """
        DELETE FROM bioactivities
        WHERE compound_id = %s
          AND assay_type IS NULL
        """,
        (compound_id,),
    )
    return cur.rowcount


# Alias de compatibilidade: chamadas legadas a insert_bioactivity continuam
# funcionando (recebem dict cru — passamos pelo normalize_bioactivity).
def insert_bioactivity(cur, compound_id: str, target_id: str, act: dict):
    """DEPRECATED: use upsert_bioactivity(cur, c_id, t_id, normalize_bioactivity(act))."""
    from .chembl_client import normalize_bioactivity
    upsert_bioactivity(cur, compound_id, target_id, normalize_bioactivity(act))


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
    # variant_sequence: ChEMBL retorna objeto JSON (com mutation/accession/…)
    # ou None. Serializamos para JSONB via psycopg2 — passamos json.dumps().
    variant = mec.get("variant_sequence")
    variant_json = json.dumps(variant) if variant else None

    cur.execute(
        """
        INSERT INTO mechanisms (
            mec_id, compound_id, target_id, target_chembl_id, target_name,
            mechanism_of_action, action_type,
            direct_interaction, disease_efficacy,
            mechanism_comment, selectivity_comment, binding_site_comment,
            variant_sequence
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (mec_id) DO UPDATE SET
            target_id            = COALESCE(EXCLUDED.target_id,            mechanisms.target_id),
            mechanism_of_action  = COALESCE(EXCLUDED.mechanism_of_action,  mechanisms.mechanism_of_action),
            action_type          = COALESCE(EXCLUDED.action_type,          mechanisms.action_type),
            mechanism_comment    = COALESCE(EXCLUDED.mechanism_comment,    mechanisms.mechanism_comment),
            selectivity_comment  = COALESCE(EXCLUDED.selectivity_comment,  mechanisms.selectivity_comment),
            binding_site_comment = COALESCE(EXCLUDED.binding_site_comment, mechanisms.binding_site_comment),
            variant_sequence     = COALESCE(EXCLUDED.variant_sequence,     mechanisms.variant_sequence)
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
            variant_json,
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