"""
schemas.py
----------
Modelos Pydantic v2 que descrevem o contrato de resposta da API (api.py).

Por que existem
---------------
- documentar shape exato no Swagger/ReDoc (antes era `dict` opaco);
- validar tipo na borda — Decimals viram floats, NULLs ficam Optional;
- dar ao frontend React um contrato estável para gerar types.

Decisões de tipagem
-------------------
- Decimal do psycopg2 → declarado como `float` (Pydantic v2 coage em modo lax).
- IDs surrogate (UUID, mec_id, drugind_id, pmid) → str/int conforme a tabela.
- Colunas JSONB já desserializadas (mesh_terms, keywords, pub_types, authors,
  compounds) → `Optional[list]`; o conteúdo varia (lista de strings ou objetos).
- Campos vindos de COUNT(...) ou SUM(...) → int com default 0.
- `extra='ignore'` no Config base — handlers podem devolver dicts com mais
  chaves; descartamos silenciosamente.
"""

from __future__ import annotations

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ============================================================
# Envelope paginado genérico (output de _paginate())
# ============================================================

class Page(_Base, Generic[T]):
    page:  int
    size:  int
    total: int
    pages: int
    items: List[T]


# ============================================================
# Geral
# ============================================================

class RootResponse(_Base):
    name:      str
    version:   str
    docs:      str
    redoc:     str
    endpoints: List[str]


class HealthResponse(_Base):
    status:    str
    compounds: int


class StatsResponse(_Base):
    compounds:               int
    articles:                int
    articles_with_abstract:  int
    indications:             int
    approved_indications:    int
    mechanisms:              int
    bioactivities:           int
    targets:                 int
    compounds_with_admet:    int
    avg_qed:                 Optional[float] = None
    latest_article_year:     Optional[int]   = None

    # ── Drug pipeline (migration 0004) ───────────────────────
    approved_drugs:          int = 0
    phase3_drugs:            int = 0
    withdrawn_drugs:         int = 0
    black_box_drugs:         int = 0
    oral_drugs:              int = 0
    parenteral_drugs:        int = 0
    first_in_class_drugs:    int = 0
    orphan_drugs:            int = 0
    distinct_molecule_types: int = 0
    total_synonyms:          int = 0
    total_atc_codes:         int = 0

    # ── Bioactivity quality (migration 0005) ────────────────
    bioactivities_with_pchembl:  int = 0
    potent_bioactivities:        int = 0
    bioactivities_with_mutation: int = 0
    distinct_assay_types:        int = 0
    distinct_journals:           int = 0

    # ── Target enrichment (migration 0006) ──────────────────
    enriched_targets:        int = 0
    distinct_genes:          int = 0
    total_pdb_structures:    int = 0

    # ── Mechanism variants (migration 0007) ─────────────────
    mechanisms_with_variant: int = 0

    # ── Clinical Trials (migration 0003) ────────────────────
    total_trials:            int = 0
    compounds_with_trials:   int = 0


# ============================================================
# Compostos
# ============================================================

class CompoundListItem(_Base):
    chembl_id:          str
    name:               Optional[str]   = None
    molecular_formula:  Optional[str]   = None
    mol_weight:         Optional[float] = None
    smiles:             Optional[str]   = None
    qed:                Optional[float] = None
    alogp:              Optional[float] = None
    psa:                Optional[float] = None
    hbd:                Optional[int]   = None
    hba:                Optional[int]   = None
    ro5_violations:     Optional[int]   = None
    max_clinical_phase: Optional[float] = None
    total_indications:  int = 0
    total_articles:     int = 0


class CompoundSynonym(_Base):
    synonym:  str
    syn_type: Optional[str] = None


class CompoundAtc(_Base):
    level5:             str
    level1:             Optional[str] = None
    level1_description: Optional[str] = None
    level2:             Optional[str] = None
    level2_description: Optional[str] = None
    level3:             Optional[str] = None
    level3_description: Optional[str] = None
    level4:             Optional[str] = None
    level4_description: Optional[str] = None


class CompoundDetail(_Base):
    id:                 str
    chembl_id:          str
    name:               Optional[str]   = None
    molecular_formula:  Optional[str]   = None
    mol_weight:         Optional[float] = None
    smiles:             Optional[str]   = None
    inchi:              Optional[str]   = None
    inchi_key:          Optional[str]   = None
    created_at:         Optional[str]   = None

    # Metadata clínico/regulatório (migration 0004)
    max_phase:            Optional[float] = None
    first_approval:       Optional[int]   = None
    molecule_type:        Optional[str]   = None
    oral:                 Optional[bool]  = None
    parenteral:           Optional[bool]  = None
    topical:              Optional[bool]  = None
    black_box_warning:    Optional[bool]  = None
    withdrawn_flag:       Optional[bool]  = None
    withdrawn_reason:     Optional[str]   = None
    withdrawn_year:       Optional[int]   = None
    withdrawn_country:    Optional[str]   = None
    withdrawn_class:      Optional[str]   = None
    prodrug:              Optional[bool]  = None
    natural_product:      Optional[bool]  = None
    therapeutic_flag:     Optional[bool]  = None
    first_in_class:       Optional[bool]  = None
    orphan:               Optional[bool]  = None
    chirality:            Optional[int]   = None
    availability_type:    Optional[int]   = None
    usan_stem:            Optional[str]   = None
    usan_stem_definition: Optional[str]   = None
    usan_year:            Optional[int]   = None
    np_likeness_score:    Optional[float] = None

    synonyms: List[CompoundSynonym] = []
    atc:      List[CompoundAtc]     = []


class AdmetResponse(_Base):
    chembl_id:          str
    alogp:              Optional[float] = None
    cx_logp:            Optional[float] = None
    cx_logd:            Optional[float] = None
    cx_most_apka:       Optional[float] = None
    cx_most_bpka:       Optional[float] = None
    molecular_species:  Optional[str]   = None
    mw_freebase:        Optional[float] = None
    mw_monoisotopic:    Optional[float] = None
    heavy_atoms:        Optional[int]   = None
    aromatic_rings:     Optional[int]   = None
    rtb:                Optional[int]   = None
    hbd:                Optional[int]   = None
    hbd_lipinski:       Optional[int]   = None
    hba:                Optional[int]   = None
    hba_lipinski:       Optional[int]   = None
    psa:                Optional[float] = None
    num_ro5_violations: Optional[int]   = None
    ro3_pass:           Optional[str]   = None
    qed_weighted:       Optional[float] = None
    num_alerts:         Optional[int]   = None
    lipinski_pass:      Optional[bool]  = None
    veber_pass:         Optional[bool]  = None
    pains_free:         Optional[bool]  = None


# ============================================================
# Indicações / Mecanismos / Bioatividades
# ============================================================

class IndicationItem(_Base):
    drugind_id:   Optional[int]   = None
    mesh_id:      Optional[str]   = None
    mesh_heading: Optional[str]   = None
    efo_id:       Optional[str]   = None
    efo_term:     Optional[str]   = None
    max_phase:    Optional[float] = None
    phase_label:  str


class IndicationsResponse(Page[IndicationItem]):
    chembl_id: str


class MechanismItem(_Base):
    mec_id:               Optional[int]  = None
    mechanism_of_action:  Optional[str]  = None
    action_type:          Optional[str]  = None
    target_chembl_id:     Optional[str]  = None
    target_name:          Optional[str]  = None
    direct_interaction:   Optional[bool] = None
    disease_efficacy:     Optional[bool] = None
    mechanism_comment:    Optional[str]  = None
    selectivity_comment:  Optional[str]  = None
    binding_site_comment: Optional[str]  = None

    # Target enrichment (migration 0006) + variant_sequence (0007)
    gene_symbol:          Optional[str]  = None
    uniprot_accession:    Optional[str]  = None
    variant_sequence:     Optional[dict] = None


class MechanismsResponse(_Base):
    chembl_id: str
    total:     int
    items:     List[MechanismItem]


class BioactivityItem(_Base):
    target_chembl_id: Optional[str]   = None
    target_name:      Optional[str]   = None
    organism:         Optional[str]   = None
    activity_type:    Optional[str]   = None
    value:            Optional[float] = None
    units:            Optional[str]   = None
    relation:         Optional[str]   = None

    # Target enrichment (migration 0006)
    gene_symbol:       Optional[str] = None
    uniprot_accession: Optional[str] = None

    # Enriquecimento (migration 0005)
    pchembl_value:         Optional[float] = None
    standard_value:        Optional[float] = None
    standard_units:        Optional[str]   = None
    assay_chembl_id:       Optional[str]   = None
    assay_type:            Optional[str]   = None    # B|F|A|T|P
    assay_description:     Optional[str]   = None
    bao_label:             Optional[str]   = None
    document_journal:      Optional[str]   = None
    document_year:         Optional[int]   = None
    bei:                   Optional[float] = None
    le:                    Optional[float] = None
    lle:                   Optional[float] = None
    sei:                   Optional[float] = None
    data_validity_comment: Optional[str]   = None
    assay_variant_mutation: Optional[str]  = None


class BioactivitiesResponse(Page[BioactivityItem]):
    chembl_id: str


# ============================================================
# Artigos
# ============================================================

class ArticleListItem(_Base):
    pmid:             str
    title:            Optional[str]  = None
    journal:          Optional[str]  = None
    pub_year:         Optional[int]  = None
    doi:              Optional[str]  = None
    abstract_snippet: Optional[str]  = None
    pub_types:        Optional[list] = None
    compounds:        Optional[str]  = None


class ArticleDetail(_Base):
    pmid:       str
    title:      Optional[str]  = None
    abstract:   Optional[str]  = None
    authors:    Optional[list] = None
    journal:    Optional[str]  = None
    pub_year:   Optional[int]  = None
    doi:        Optional[str]  = None
    mesh_terms: Optional[list] = None
    keywords:   Optional[list] = None
    pub_types:  Optional[list] = None
    compounds:  Optional[list] = None


class CompoundArticleItem(_Base):
    pmid:       str
    title:      Optional[str]  = None
    journal:    Optional[str]  = None
    pub_year:   Optional[int]  = None
    doi:        Optional[str]  = None
    abstract:   Optional[str]  = None
    mesh_terms: Optional[list] = None
    keywords:   Optional[list] = None
    pub_types:  Optional[list] = None


class CompoundArticlesResponse(Page[CompoundArticleItem]):
    chembl_id: str


# ============================================================
# Alvos biológicos
# ============================================================

class TargetListItem(_Base):
    chembl_id:        str
    name:             Optional[str] = None
    type:             Optional[str] = None
    organism:         Optional[str] = None
    compounds_tested: int = 0


class TargetComponent(_Base):
    accession:             Optional[str] = None    # UniProt
    gene_symbol:           Optional[str] = None    # ABL1
    component_type:        Optional[str] = None    # PROTEIN | RNA | …
    component_description: Optional[str] = None
    relationship:          Optional[str] = None


class TargetGoTerm(_Base):
    category: str    # GoFunction | GoProcess | GoComponent
    go_id:    str    # GO:0005524
    term:     Optional[str] = None


class TargetXrefGroup(_Base):
    src_db: str
    ids:    List[str] = []


class TargetBioStats(_Base):
    total_bioactivities:    int = 0
    distinct_compounds:     int = 0
    bioactivities_with_pchembl: int = 0
    potent_bioactivities:   int = 0       # pchembl >= 7
    median_pchembl:         Optional[float] = None
    distinct_assay_types:   int = 0
    distinct_activity_types: int = 0


class TargetDetail(_Base):
    chembl_id:           str
    name:                Optional[str] = None
    type:                Optional[str] = None
    organism:            Optional[str] = None
    tax_id:              Optional[int] = None
    species_group_flag:  Optional[bool] = None
    components:          List[TargetComponent] = []
    pdb_ids:             List[str]      = []
    go_terms:            List[TargetGoTerm] = []
    xrefs:               List[TargetXrefGroup] = []
    stats:               TargetBioStats


class TargetCompoundItem(_Base):
    chembl_id:          str
    name:               Optional[str]   = None
    max_clinical_phase: Optional[float] = None
    qed:                Optional[float] = None
    best_pchembl:       Optional[float] = None
    best_activity_type: Optional[str]   = None
    best_value:         Optional[float] = None
    best_units:         Optional[str]   = None
    n_bioactivities:    int = 0


class TargetCompoundsResponse(Page[TargetCompoundItem]):
    chembl_id: str


class TargetBioactivityItem(_Base):
    compound_chembl_id: str
    compound_name:      Optional[str]   = None
    activity_type:      Optional[str]   = None
    value:              Optional[float] = None
    units:              Optional[str]   = None
    relation:           Optional[str]   = None
    pchembl_value:      Optional[float] = None
    standard_value:     Optional[float] = None
    standard_units:     Optional[str]   = None
    assay_chembl_id:    Optional[str]   = None
    assay_type:         Optional[str]   = None
    assay_description:  Optional[str]   = None
    document_year:      Optional[int]   = None
    document_journal:   Optional[str]   = None


class TargetBioactivitiesResponse(Page[TargetBioactivityItem]):
    chembl_id: str


# ============================================================
# Busca full-text unificada
# ============================================================

class SearchHit(_Base):
    source:    str
    id:        str
    label:     Optional[str]   = None
    detail:    Optional[str]   = None
    rank:      Optional[float] = None
    highlight: Optional[str]   = None


class SearchResponse(_Base):
    query: str
    page:  int
    size:  int
    total: int
    pages: int
    items: List[SearchHit]


# ============================================================
# Ensaios clínicos (ClinicalTrials.gov)
# ============================================================

class TrialKPIs(_Base):
    total_trials:        int               = 0
    recruiting_trials:   int               = 0
    completed_trials:    int               = 0
    phase3_trials:       int               = 0
    phase4_trials:       int               = 0
    unique_sponsors:     int               = 0
    latest_trial_start:  Optional[str]     = None


class TrialRow(_Base):
    nct_id:                   str
    title:                    Optional[str]       = None
    status:                   Optional[str]       = None
    phases:                   Optional[List[str]] = None
    conditions:               Optional[List[str]] = None
    interventions:            Optional[List[str]] = None
    sponsor:                  Optional[str]       = None
    enrollment:               Optional[int]       = None
    start_date:               Optional[str]       = None
    primary_completion_date:  Optional[str]       = None
    locations_count:          Optional[int]       = 0
    study_type:               Optional[str]       = None
    primary_endpoint:         Optional[str]       = None
    intervention_name:        Optional[str]       = None
    match_method:             Optional[str]       = None
    match_confidence:         Optional[float]     = None
    last_synced_at:           Optional[str]       = None


class TrialsResponse(Page[TrialRow]):
    chembl_id: str
    kpis:      TrialKPIs


class SyncResponse(_Base):
    chembl_id:        str
    drug_name:        str
    trials_fetched:   int
    trials_upserted:  int
    links_created:    int


# ============================================================
# Trials globais (lista cross-composto)
# ============================================================

class TrialGlobalListItem(_Base):
    nct_id:                  str
    title:                   Optional[str]       = None
    status:                  Optional[str]       = None
    phases:                  Optional[List[str]] = None
    conditions:              Optional[List[str]] = None
    interventions:           Optional[List[str]] = None
    sponsor:                 Optional[str]       = None
    enrollment:              Optional[int]       = None
    start_date:              Optional[str]       = None
    primary_completion_date: Optional[str]       = None
    locations_count:         Optional[int]       = 0
    study_type:              Optional[str]       = None
    primary_endpoint:        Optional[str]       = None
    # Lista de chembl_ids agregada (vinda de compound_clinical_trials)
    chembl_ids:              Optional[List[str]] = None
    compounds:               Optional[List[str]] = None


class TrialsGlobalStats(_Base):
    total_trials:        int = 0
    recruiting_trials:   int = 0
    completed_trials:    int = 0
    phase3_trials:       int = 0
    phase4_trials:       int = 0
    interventional:      int = 0
    observational:       int = 0
    unique_sponsors:     int = 0
    unique_conditions:   int = 0
    distinct_compounds_with_trials: int = 0
    latest_trial_start:  Optional[str] = None
    by_status:           dict          = {}     # status → count
    by_phase:            dict          = {}     # phase → count


class SponsorAggItem(_Base):
    sponsor:           str
    trial_count:       int
    recruiting_trials: int = 0
    phase3_trials:     int = 0
    phase4_trials:     int = 0


class ConditionAggItem(_Base):
    condition:    str
    trial_count:  int


class EndpointBucket(_Base):
    pattern:  str
    label:    str
    matches:  int
    examples: List[str] = []     # NCT ids amostrais


class EndpointAnalysisResponse(_Base):
    total_with_endpoint: int
    buckets:             List[EndpointBucket]
    top_phrases:         List[dict] = []     # [{phrase, count}]
