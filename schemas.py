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


class CompoundDetail(_Base):
    id:                 str
    chembl_id:          str
    name:               Optional[str]   = None
    molecular_formula:  Optional[str]   = None
    mol_weight:         Optional[float] = None
    smiles:             Optional[str]   = None
    inchi_key:          Optional[str]   = None
    created_at:         Optional[str]   = None


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
