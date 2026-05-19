"""
api.py
------
API REST com FastAPI para explorar o banco ChEMBL + PubMed.

Instalação:
    pip install fastapi uvicorn psycopg2-binary

Execução:
    uvicorn api:app --reload --port 8000

Documentação interativa (Swagger):
    http://localhost:8000/docs

Documentação alternativa (ReDoc):
    http://localhost:8000/redoc

Endpoints:
    GET  /                                    Informações da API
    GET  /health                              Status do banco
    GET  /compounds                           Lista compostos (paginado, filtros)
    GET  /compounds/{chembl_id}               Composto completo
    GET  /compounds/{chembl_id}/admet         Propriedades ADMET
    GET  /compounds/{chembl_id}/indications   Indicações terapêuticas
    GET  /compounds/{chembl_id}/mechanisms    Mecanismos de ação
    GET  /compounds/{chembl_id}/bioactivities Bioatividades
    GET  /compounds/{chembl_id}/articles      Artigos do PubMed
    GET  /articles                            Lista artigos (paginado, filtros)
    GET  /articles/{pmid}                     Artigo completo
    GET  /targets                             Lista alvos biológicos
    GET  /search                              Busca full-text unificada
    GET  /stats                               Estatísticas do banco
"""

import json
import os
from contextlib import asynccontextmanager
from typing import Any, Optional

import psycopg2
import psycopg2.extras
import psycopg2.pool
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from populate.config import DB_CONFIG, is_dev
from schemas import (
    AdmetResponse,
    ArticleDetail,
    ArticleListItem,
    BioactivitiesResponse,
    CompoundArticlesResponse,
    CompoundDetail,
    CompoundListItem,
    HealthResponse,
    IndicationsResponse,
    MechanismsResponse,
    Page,
    RootResponse,
    SearchResponse,
    StatsResponse,
    TargetListItem,
)

# ============================================================
# Configuração do banco
# ============================================================
# DB_CONFIG é resolvido em populate/config.py a partir de:
#   1. DATABASE_URL  (Supabase, Railway, Render, Heroku...)
#   2. variáveis individuais DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_SSLMODE
#   3. defaults locais do Docker (localhost / chembl_pubmed / admin / admin123)

# Pool de conexões — reutiliza conexões entre requests
_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pool
    _pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=2, maxconn=10, **DB_CONFIG
    )
    yield
    _pool.closeall()


def get_cursor():
    """Retorna um cursor com DictCursor do pool."""
    conn = _pool.getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        _pool.putconn(conn)


def db_query(sql: str, params=None) -> list[dict]:
    """Executa uma query e retorna lista de dicts."""
    conn = _pool.getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.commit()
        return [dict(r) for r in rows]
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        _pool.putconn(conn)


def db_one(sql: str, params=None) -> Optional[dict]:
    """Executa uma query e retorna um único dict ou None."""
    rows = db_query(sql, params)
    return rows[0] if rows else None


# ============================================================
# App FastAPI
# ============================================================

app = FastAPI(
    title="DrugXpert API",
    description=(
        "API REST para consulta do banco farmacológico ChEMBL + PubMed. "
        "Dados incluem compostos, propriedades ADMET, indicações terapêuticas, "
        "mecanismos de ação e artigos científicos."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ============================================================
# CORS
# ============================================================
# Origens permitidas vêm de CORS_ALLOW_ORIGINS (lista separada por vírgula).
# Em ambiente NÃO-dev a variável é OBRIGATÓRIA — refuse-by-default evita
# expor a API publicamente por acidente.
_DEV_CORS_DEFAULT = [
    "http://localhost:5173",   # Vite (frontend React)
    "http://127.0.0.1:5173",
    "http://localhost:8501",   # Streamlit dashboard, se chamar a API
]

_cors_env = os.environ.get("CORS_ALLOW_ORIGINS", "").strip()
if _cors_env:
    _cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]
elif is_dev():
    _cors_origins = _DEV_CORS_DEFAULT
else:
    raise RuntimeError(
        "CORS_ALLOW_ORIGINS não foi definido em ambiente não-dev. "
        "Defina a variável com a lista de origens permitidas, ex: "
        "CORS_ALLOW_ORIGINS='https://app.example.com,https://admin.example.com'. "
        "Use APP_ENV=development para liberar localhost automaticamente."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ============================================================
# Helpers
# ============================================================

def _parse_jsonb(value: Any) -> Any:
    """Converte campo JSONB (string ou None) para objeto Python."""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


def _paginate(sql_base: str, params: list, page: int, size: int) -> dict:
    """
    Executa a query com LIMIT/OFFSET e retorna envelope paginado.
    sql_base deve ter um SELECT principal sem ORDER já aplicado.
    """
    count_sql = f"SELECT COUNT(*) AS total FROM ({sql_base}) _sub"
    total_row = db_one(count_sql, params)
    total     = total_row["total"] if total_row else 0

    paged_sql = f"{sql_base} LIMIT %s OFFSET %s"
    items     = db_query(paged_sql, params + [size, (page - 1) * size])

    return {
        "page":     page,
        "size":     size,
        "total":    total,
        "pages":    (total + size - 1) // size,
        "items":    items,
    }


def _compound_not_found(chembl_id: str):
    raise HTTPException(404, detail=f"Composto '{chembl_id}' não encontrado.")


def _resolve_compound_id(chembl_id: str) -> str:
    """Retorna o UUID interno do composto ou lança 404."""
    row = db_one(
        "SELECT id::text FROM compounds WHERE chembl_id = %s",
        (chembl_id.upper(),),
    )
    if not row:
        _compound_not_found(chembl_id)
    return row["id"]


# ============================================================
# Rotas — raiz e saúde
# ============================================================

@app.get("/", tags=["geral"], summary="Informações da API", response_model=RootResponse)
def root():
    return {
        "name":    "DrugXpert API",
        "version": "1.0.0",
        "docs":    "/docs",
        "redoc":   "/redoc",
        "endpoints": [
            "GET /compounds",
            "GET /compounds/{chembl_id}",
            "GET /compounds/{chembl_id}/admet",
            "GET /compounds/{chembl_id}/indications",
            "GET /compounds/{chembl_id}/mechanisms",
            "GET /compounds/{chembl_id}/bioactivities",
            "GET /compounds/{chembl_id}/articles",
            "GET /articles",
            "GET /articles/{pmid}",
            "GET /targets",
            "GET /search",
            "GET /stats",
        ],
    }


@app.get("/health", tags=["geral"], summary="Status do banco", response_model=HealthResponse)
def health():
    try:
        row = db_one("SELECT COUNT(*) AS compounds FROM compounds")
        return {"status": "ok", "compounds": row["compounds"]}
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": str(exc)},
        )


# ============================================================
# Rotas — compostos
# ============================================================

@app.get(
    "/compounds",
    tags=["compostos"],
    summary="Lista compostos",
    response_model=Page[CompoundListItem],
)
def list_compounds(
    q:          Optional[str]   = Query(None,  description="Filtro por nome (parcial, case-insensitive)"),
    min_qed:    Optional[float] = Query(None,  description="QED mínimo (0–1)", ge=0, le=1),
    max_qed:    Optional[float] = Query(None,  description="QED máximo (0–1)", ge=0, le=1),
    lipinski:   Optional[bool]  = Query(None,  description="Só compostos que passam no Lipinski (ro5_violations=0)"),
    min_mw:     Optional[float] = Query(None,  description="Peso molecular mínimo"),
    max_mw:     Optional[float] = Query(None,  description="Peso molecular máximo"),
    min_phase:  Optional[float] = Query(None,  description="Fase clínica mínima (ex: 4 = aprovado)"),
    sort_by:    str             = Query("name", description="Campo de ordenação: name | qed | mol_weight"),
    sort_order: str             = Query("asc",  description="Direção: asc | desc"),
    page:       int             = Query(1,      description="Página", ge=1),
    size:       int             = Query(20,     description="Itens por página", ge=1, le=100),
):
    valid_sorts = {"name": "c.name", "qed": "a.qed_weighted", "mol_weight": "c.mol_weight"}
    order_col   = valid_sorts.get(sort_by, "c.name")
    order_dir   = "DESC" if sort_order.lower() == "desc" else "ASC"

    sql = """
        SELECT
            c.chembl_id,
            c.name,
            c.molecular_formula,
            ROUND(c.mol_weight::numeric, 2)       AS mol_weight,
            c.smiles,
            ROUND(a.qed_weighted::numeric, 4)     AS qed,
            ROUND(a.alogp::numeric, 2)            AS alogp,
            ROUND(a.psa::numeric, 2)              AS psa,
            a.hbd,
            a.hba,
            a.num_ro5_violations                  AS ro5_violations,
            (SELECT MAX(i.max_phase)
             FROM indications i WHERE i.compound_id = c.id) AS max_clinical_phase,
            (SELECT COUNT(*)
             FROM indications i WHERE i.compound_id = c.id) AS total_indications,
            (SELECT COUNT(*)
             FROM article_compounds ac WHERE ac.compound_id = c.id) AS total_articles
        FROM compounds c
        LEFT JOIN admet_properties a ON a.compound_id = c.id
        WHERE 1=1
    """
    params = []

    if q:
        sql += " AND LOWER(c.name) LIKE LOWER(%s)"
        params.append(f"%{q}%")
    if min_qed is not None:
        sql += " AND a.qed_weighted >= %s"
        params.append(min_qed)
    if max_qed is not None:
        sql += " AND a.qed_weighted <= %s"
        params.append(max_qed)
    if lipinski is True:
        sql += " AND a.num_ro5_violations = 0"
    if lipinski is False:
        sql += " AND a.num_ro5_violations > 0"
    if min_mw is not None:
        sql += " AND c.mol_weight >= %s"
        params.append(min_mw)
    if max_mw is not None:
        sql += " AND c.mol_weight <= %s"
        params.append(max_mw)
    if min_phase is not None:
        sql += """
            AND EXISTS (
                SELECT 1 FROM indications i
                WHERE i.compound_id = c.id AND i.max_phase >= %s
            )
        """
        params.append(min_phase)

    sql += f" ORDER BY {order_col} {order_dir} NULLS LAST"

    return _paginate(sql, params, page, size)


@app.get(
    "/compounds/{chembl_id}",
    tags=["compostos"],
    summary="Composto completo",
    response_model=CompoundDetail,
)
def get_compound(chembl_id: str):
    row = db_one("""
        SELECT
            c.id::text,
            c.chembl_id,
            c.name,
            c.molecular_formula,
            ROUND(c.mol_weight::numeric, 2) AS mol_weight,
            c.smiles,
            c.inchi,
            c.inchi_key,

            -- Metadata clínico/regulatório (migration 0004)
            c.max_phase,
            c.first_approval,
            c.molecule_type,
            c.oral, c.parenteral, c.topical,
            c.black_box_warning,
            c.withdrawn_flag, c.withdrawn_reason, c.withdrawn_year,
            c.withdrawn_country, c.withdrawn_class,
            c.prodrug, c.natural_product, c.therapeutic_flag,
            c.first_in_class, c.orphan,
            c.chirality, c.availability_type,
            c.usan_stem, c.usan_stem_definition, c.usan_year,
            c.np_likeness_score,

            -- Sinônimos e ATC inline (evita round-trips do frontend)
            COALESCE(
                (SELECT jsonb_agg(jsonb_build_object(
                            'synonym',  s.synonym,
                            'syn_type', s.syn_type)
                         ORDER BY s.syn_type, s.synonym)
                 FROM compound_synonyms s
                 WHERE s.compound_id = c.id),
                '[]'::jsonb
            ) AS synonyms,
            COALESCE(
                (SELECT jsonb_agg(jsonb_build_object(
                            'level5',             a.level5,
                            'level1',             a.level1,
                            'level1_description', a.level1_description,
                            'level2',             a.level2,
                            'level2_description', a.level2_description,
                            'level3',             a.level3,
                            'level3_description', a.level3_description,
                            'level4',             a.level4,
                            'level4_description', a.level4_description)
                         ORDER BY a.level5)
                 FROM compound_atc a
                 WHERE a.compound_id = c.id),
                '[]'::jsonb
            ) AS atc,

            c.created_at::text
        FROM compounds c
        WHERE c.chembl_id = %s
    """, (chembl_id.upper(),))

    if not row:
        _compound_not_found(chembl_id)

    return row


@app.get(
    "/compounds/{chembl_id}/admet",
    tags=["compostos"],
    summary="Propriedades ADMET",
    response_model=AdmetResponse,
)
def get_compound_admet(chembl_id: str):
    compound_id = _resolve_compound_id(chembl_id)

    row = db_one("""
        SELECT
            ROUND(a.alogp::numeric,           3) AS alogp,
            ROUND(a.cx_logp::numeric,         3) AS cx_logp,
            ROUND(a.cx_logd::numeric,         3) AS cx_logd,
            ROUND(a.cx_most_apka::numeric,    3) AS cx_most_apka,
            ROUND(a.cx_most_bpka::numeric,    3) AS cx_most_bpka,
            a.molecular_species,
            ROUND(a.mw_freebase::numeric,     2) AS mw_freebase,
            ROUND(a.mw_monoisotopic::numeric, 4) AS mw_monoisotopic,
            a.heavy_atoms,
            a.aromatic_rings,
            a.rtb,
            a.hbd,
            a.hbd_lipinski,
            a.hba,
            a.hba_lipinski,
            ROUND(a.psa::numeric,             2) AS psa,
            a.num_ro5_violations,
            a.ro3_pass,
            ROUND(a.qed_weighted::numeric,    4) AS qed_weighted,
            a.num_alerts,
            -- Flags calculados
            (a.num_ro5_violations = 0)                        AS lipinski_pass,
            (COALESCE(a.rtb, 99) <= 10
             AND COALESCE(a.psa, 999) <= 140)                 AS veber_pass,
            (COALESCE(a.num_alerts, 1) = 0)                   AS pains_free
        FROM admet_properties a
        WHERE a.compound_id = %s
    """, (compound_id,))

    if not row:
        raise HTTPException(404, detail="Dados ADMET não encontrados para este composto.")

    return {"chembl_id": chembl_id.upper(), **row}


@app.get(
    "/compounds/{chembl_id}/indications",
    tags=["compostos"],
    summary="Indicações terapêuticas",
    response_model=IndicationsResponse,
)
def get_compound_indications(
    chembl_id: str,
    min_phase: Optional[float] = Query(None, description="Fase clínica mínima (ex: 4 = aprovado)"),
    page:      int             = Query(1,    ge=1),
    size:      int             = Query(50,   ge=1, le=200),
):
    compound_id = _resolve_compound_id(chembl_id)

    sql = """
        SELECT
            i.drugind_id,
            i.mesh_id,
            i.mesh_heading,
            i.efo_id,
            i.efo_term,
            i.max_phase,
            CASE i.max_phase
                WHEN 4   THEN 'Approved'
                WHEN 3   THEN 'Phase 3'
                WHEN 2   THEN 'Phase 2'
                WHEN 1   THEN 'Phase 1'
                WHEN 0.5 THEN 'Early Phase 1'
                ELSE          'Preclinical'
            END AS phase_label
        FROM indications i
        WHERE i.compound_id = %s
    """
    params = [compound_id]

    if min_phase is not None:
        sql += " AND i.max_phase >= %s"
        params.append(min_phase)

    sql += " ORDER BY i.max_phase DESC NULLS LAST, i.mesh_heading"

    result = _paginate(sql, params, page, size)
    result["chembl_id"] = chembl_id.upper()
    return result


@app.get(
    "/compounds/{chembl_id}/mechanisms",
    tags=["compostos"],
    summary="Mecanismos de ação",
    response_model=MechanismsResponse,
)
def get_compound_mechanisms(chembl_id: str):
    compound_id = _resolve_compound_id(chembl_id)

    # LATERAL pega o "primeiro" componente do target (geralmente o único —
    # SINGLE PROTEIN), e expõe gene_symbol / accession diretamente.
    rows = db_query("""
        SELECT
            m.mec_id,
            m.mechanism_of_action,
            m.action_type,
            m.target_chembl_id,
            m.target_name,
            m.direct_interaction,
            m.disease_efficacy,
            m.mechanism_comment,
            m.selectivity_comment,
            m.binding_site_comment,
            m.variant_sequence,
            tc.gene_symbol,
            tc.accession                       AS uniprot_accession
        FROM mechanisms m
        LEFT JOIN LATERAL (
            SELECT gene_symbol, accession
            FROM target_components
            WHERE target_id = m.target_id
            ORDER BY component_id
            LIMIT 1
        ) tc ON TRUE
        WHERE m.compound_id = %s
        ORDER BY m.action_type, m.target_name
    """, (compound_id,))

    return {"chembl_id": chembl_id.upper(), "total": len(rows), "items": rows}


@app.get(
    "/compounds/{chembl_id}/bioactivities",
    tags=["compostos"],
    summary="Bioatividades",
    response_model=BioactivitiesResponse,
)
def get_compound_bioactivities(
    chembl_id:     str,
    activity_type: Optional[str]   = Query(None, description="Tipo: IC50, Ki, EC50..."),
    assay_type:    Optional[str]   = Query(None, description="Tipo de ensaio: B (binding), F (functional), A (ADME), T (toxicity), P (physchem)"),
    min_pchembl:   Optional[float] = Query(None, description="Filtra por pChEMBL mínimo (≥7 = potente <100nM)", ge=0, le=14),
    page:          int             = Query(1,    ge=1),
    size:          int             = Query(20,   ge=1, le=100),
):
    compound_id = _resolve_compound_id(chembl_id)

    sql = """
        SELECT
            t.chembl_id AS target_chembl_id,
            t.name      AS target_name,
            COALESCE(b.target_organism, t.organism)  AS organism,
            tc.gene_symbol,
            tc.accession                              AS uniprot_accession,
            b.activity_type,
            b.value,
            b.units,
            b.relation,
            ROUND(b.pchembl_value::numeric, 2)       AS pchembl_value,
            ROUND(b.standard_value::numeric, 4)      AS standard_value,
            b.standard_units,
            b.assay_chembl_id,
            b.assay_type,
            b.assay_description,
            b.bao_label,
            b.document_journal,
            b.document_year,
            ROUND(b.bei::numeric, 2)                 AS bei,
            ROUND(b.le::numeric,  2)                 AS le,
            ROUND(b.lle::numeric, 2)                 AS lle,
            ROUND(b.sei::numeric, 2)                 AS sei,
            b.data_validity_comment,
            b.assay_variant_mutation
        FROM bioactivities b
        JOIN targets t ON t.id = b.target_id
        LEFT JOIN LATERAL (
            SELECT gene_symbol, accession
            FROM target_components
            WHERE target_id = t.id
            ORDER BY component_id
            LIMIT 1
        ) tc ON TRUE
        WHERE b.compound_id = %s
    """
    params = [compound_id]

    if activity_type:
        sql += " AND UPPER(b.activity_type) = UPPER(%s)"
        params.append(activity_type)
    if assay_type:
        sql += " AND UPPER(b.assay_type) = UPPER(%s)"
        params.append(assay_type)
    if min_pchembl is not None:
        sql += " AND b.pchembl_value >= %s"
        params.append(min_pchembl)

    # Ordenação: mais potentes primeiro (pchembl desc); empata por activity_type.
    sql += " ORDER BY b.pchembl_value DESC NULLS LAST, b.activity_type, b.value"

    result = _paginate(sql, params, page, size)
    result["chembl_id"] = chembl_id.upper()
    return result


@app.get(
    "/compounds/{chembl_id}/articles",
    tags=["compostos"],
    summary="Artigos do PubMed",
    response_model=CompoundArticlesResponse,
)
def get_compound_articles(
    chembl_id:    str,
    only_abstract: bool          = Query(False, description="Só artigos com abstract"),
    min_year:     Optional[int]  = Query(None,  description="Ano de publicação mínimo"),
    page:         int            = Query(1,     ge=1),
    size:         int            = Query(10,    ge=1, le=50),
):
    compound_id = _resolve_compound_id(chembl_id)

    sql = """
        SELECT
            a.pmid,
            a.title,
            a.journal,
            a.pub_year,
            a.doi,
            a.abstract,
            a.mesh_terms,
            a.keywords,
            a.pub_types
        FROM articles a
        JOIN article_compounds ac ON ac.article_id = a.id
        WHERE ac.compound_id = %s
    """
    params = [compound_id]

    if only_abstract:
        sql += " AND a.abstract IS NOT NULL"
    if min_year:
        sql += " AND a.pub_year >= %s"
        params.append(min_year)

    sql += " ORDER BY a.pub_year DESC NULLS LAST"

    result = _paginate(sql, params, page, size)

    # Deserializar campos JSONB
    for item in result["items"]:
        item["mesh_terms"] = _parse_jsonb(item.get("mesh_terms"))
        item["keywords"]   = _parse_jsonb(item.get("keywords"))
        item["pub_types"]  = _parse_jsonb(item.get("pub_types"))

    result["chembl_id"] = chembl_id.upper()
    return result


# ============================================================
# Rotas — artigos
# ============================================================

@app.get(
    "/articles",
    tags=["artigos"],
    summary="Lista artigos",
    response_model=Page[ArticleListItem],
)
def list_articles(
    q:            Optional[str] = Query(None, description="Busca no título e abstract"),
    journal:      Optional[str] = Query(None, description="Filtro por periódico"),
    min_year:     Optional[int] = Query(None, description="Ano mínimo"),
    max_year:     Optional[int] = Query(None, description="Ano máximo"),
    only_abstract: bool         = Query(False, description="Só artigos com abstract"),
    pub_type:     Optional[str] = Query(None, description="Tipo: Journal Article, Review, Clinical Trial..."),
    page:         int           = Query(1,    ge=1),
    size:         int           = Query(20,   ge=1, le=100),
):
    sql = """
        SELECT
            a.pmid,
            a.title,
            a.journal,
            a.pub_year,
            a.doi,
            LEFT(a.abstract, 300) AS abstract_snippet,
            a.pub_types,
            (SELECT STRING_AGG(DISTINCT c.name, ', ')
             FROM article_compounds ac
             JOIN compounds c ON c.id = ac.compound_id
             WHERE ac.article_id = a.id) AS compounds
        FROM articles a
        WHERE 1=1
    """
    params = []

    if q:
        sql += " AND (a.title ILIKE %s OR a.abstract ILIKE %s)"
        params += [f"%{q}%", f"%{q}%"]
    if journal:
        sql += " AND a.journal ILIKE %s"
        params.append(f"%{journal}%")
    if min_year:
        sql += " AND a.pub_year >= %s"
        params.append(min_year)
    if max_year:
        sql += " AND a.pub_year <= %s"
        params.append(max_year)
    if only_abstract:
        sql += " AND a.abstract IS NOT NULL"
    if pub_type:
        sql += " AND a.pub_types @> %s::jsonb"
        params.append(json.dumps([pub_type]))

    sql += " ORDER BY a.pub_year DESC NULLS LAST, a.title"

    result = _paginate(sql, params, page, size)
    for item in result["items"]:
        item["pub_types"] = _parse_jsonb(item.get("pub_types"))
    return result


@app.get(
    "/articles/{pmid}",
    tags=["artigos"],
    summary="Artigo completo por PMID",
    response_model=ArticleDetail,
)
def get_article(pmid: str):
    row = db_one("""
        SELECT
            a.pmid,
            a.title,
            a.abstract,
            a.authors,
            a.journal,
            a.pub_year,
            a.doi,
            a.mesh_terms,
            a.keywords,
            a.pub_types,
            (SELECT JSON_AGG(JSON_BUILD_OBJECT('name', c.name, 'chembl_id', c.chembl_id))
             FROM article_compounds ac
             JOIN compounds c ON c.id = ac.compound_id
             WHERE ac.article_id = a.id) AS compounds
        FROM articles a
        WHERE a.pmid = %s
    """, (pmid,))

    if not row:
        raise HTTPException(404, detail=f"Artigo com PMID '{pmid}' não encontrado.")

    for field in ["authors", "mesh_terms", "keywords", "pub_types", "compounds"]:
        row[field] = _parse_jsonb(row.get(field))

    return row


# ============================================================
# Rotas — alvos
# ============================================================

@app.get(
    "/targets",
    tags=["alvos"],
    summary="Lista alvos biológicos",
    response_model=Page[TargetListItem],
)
def list_targets(
    q:        Optional[str] = Query(None, description="Filtro por nome"),
    organism: Optional[str] = Query(None, description="Filtro por organismo"),
    page:     int           = Query(1,    ge=1),
    size:     int           = Query(20,   ge=1, le=100),
):
    sql = """
        SELECT
            t.chembl_id,
            t.name,
            t.type,
            t.organism,
            COUNT(DISTINCT b.compound_id) AS compounds_tested
        FROM targets t
        LEFT JOIN bioactivities b ON b.target_id = t.id
        WHERE 1=1
    """
    params = []

    if q:
        sql += " AND LOWER(t.name) LIKE LOWER(%s)"
        params.append(f"%{q}%")
    if organism:
        sql += " AND LOWER(t.organism) LIKE LOWER(%s)"
        params.append(f"%{organism}%")

    sql += " GROUP BY t.chembl_id, t.name, t.type, t.organism ORDER BY compounds_tested DESC, t.name"

    return _paginate(sql, params, page, size)


# ============================================================
# Rota — busca full-text unificada
# ============================================================

@app.get(
    "/search",
    tags=["busca"],
    summary="Busca full-text unificada",
    response_model=SearchResponse,
)
def search(
    q:      str           = Query(...,  description="Termo de busca (ex: aspirin inflammation)"),
    source: Optional[str] = Query(None, description="Filtrar por fonte: compound | article | target"),
    page:   int           = Query(1,    ge=1),
    size:   int           = Query(10,   ge=1, le=50),
):
    """
    Busca full-text em compostos, artigos e alvos usando tsvector.
    Retorna resultados ordenados por relevância com destaque do termo.
    """
    results = []

    if not source or source == "compound":
        rows = db_query("""
            SELECT
                'compound'                              AS source,
                c.chembl_id                             AS id,
                c.name                                  AS label,
                c.molecular_formula                     AS detail,
                ts_rank_cd(c.fts, plainto_tsquery('english', %s)) AS rank,
                ts_headline('english', c.name,
                    plainto_tsquery('english', %s),
                    'MaxWords=10, MinWords=3')           AS highlight
            FROM compounds c
            WHERE c.fts @@ plainto_tsquery('english', %s)
            ORDER BY rank DESC
            LIMIT %s
        """, (q, q, q, size))
        results.extend(rows)

    if not source or source == "article":
        rows = db_query("""
            SELECT
                'article'                               AS source,
                a.pmid                                  AS id,
                a.title                                 AS label,
                a.journal || COALESCE(' (' || a.pub_year::text || ')', '') AS detail,
                ts_rank_cd(a.fts, plainto_tsquery('english', %s)) AS rank,
                ts_headline('english',
                    COALESCE(a.title, '') || ' ' || COALESCE(a.abstract, ''),
                    plainto_tsquery('english', %s),
                    'MaxWords=25, MinWords=8, MaxFragments=2')   AS highlight
            FROM articles a
            WHERE a.fts @@ plainto_tsquery('english', %s)
            ORDER BY rank DESC
            LIMIT %s
        """, (q, q, q, size))
        results.extend(rows)

    if not source or source == "target":
        rows = db_query("""
            SELECT
                'target'                                AS source,
                t.chembl_id                             AS id,
                t.name                                  AS label,
                COALESCE(t.organism, '') || COALESCE(' — ' || t.type, '') AS detail,
                ts_rank_cd(t.fts, plainto_tsquery('english', %s)) AS rank,
                ts_headline('english', t.name || ' ' || COALESCE(t.organism, ''),
                    plainto_tsquery('english', %s),
                    'MaxWords=10, MinWords=3')           AS highlight
            FROM targets t
            WHERE t.fts @@ plainto_tsquery('english', %s)
            ORDER BY rank DESC
            LIMIT %s
        """, (q, q, q, size))
        results.extend(rows)

    # Ordenar por relevância e paginar manualmente
    results.sort(key=lambda r: r.get("rank") or 0, reverse=True)
    total  = len(results)
    start  = (page - 1) * size
    end    = start + size

    return {
        "query":  q,
        "page":   page,
        "size":   size,
        "total":  total,
        "pages":  (total + size - 1) // size,
        "items":  results[start:end],
    }


# ============================================================
# Rota — estatísticas
# ============================================================

@app.get(
    "/stats",
    tags=["geral"],
    summary="Estatísticas do banco",
    response_model=StatsResponse,
)
def stats():
    row = db_one("""
        SELECT
            -- ── Núcleo ───────────────────────────────────────
            (SELECT COUNT(*) FROM compounds)                    AS compounds,
            (SELECT COUNT(*) FROM articles)                     AS articles,
            (SELECT COUNT(*) FILTER (WHERE abstract IS NOT NULL)
             FROM articles)                                     AS articles_with_abstract,
            (SELECT COUNT(*) FROM indications)                  AS indications,
            (SELECT COUNT(*) FILTER (WHERE max_phase >= 4)
             FROM indications)                                  AS approved_indications,
            (SELECT COUNT(*) FROM mechanisms)                   AS mechanisms,
            (SELECT COUNT(*) FROM bioactivities)                AS bioactivities,
            (SELECT COUNT(*) FROM targets)                      AS targets,
            (SELECT COUNT(*) FROM admet_properties)             AS compounds_with_admet,
            (SELECT ROUND(AVG(qed_weighted)::numeric, 3)
             FROM admet_properties)                             AS avg_qed,
            (SELECT MAX(pub_year) FROM articles)                AS latest_article_year,

            -- ── Drug pipeline (migration 0004) ───────────────
            (SELECT COUNT(*) FROM compounds WHERE max_phase = 4)     AS approved_drugs,
            (SELECT COUNT(*) FROM compounds WHERE max_phase = 3)     AS phase3_drugs,
            (SELECT COUNT(*) FROM compounds WHERE withdrawn_flag)    AS withdrawn_drugs,
            (SELECT COUNT(*) FROM compounds WHERE black_box_warning) AS black_box_drugs,
            (SELECT COUNT(*) FROM compounds WHERE oral)              AS oral_drugs,
            (SELECT COUNT(*) FROM compounds WHERE parenteral)        AS parenteral_drugs,
            (SELECT COUNT(*) FROM compounds WHERE first_in_class)    AS first_in_class_drugs,
            (SELECT COUNT(*) FROM compounds WHERE orphan)            AS orphan_drugs,
            (SELECT COUNT(DISTINCT molecule_type)
             FROM compounds WHERE molecule_type IS NOT NULL)   AS distinct_molecule_types,
            (SELECT COUNT(*) FROM compound_synonyms)           AS total_synonyms,
            (SELECT COUNT(*) FROM compound_atc)                AS total_atc_codes,

            -- ── Bioactivity quality (migration 0005) ─────────
            (SELECT COUNT(*) FROM bioactivities
             WHERE pchembl_value IS NOT NULL)                  AS bioactivities_with_pchembl,
            (SELECT COUNT(*) FROM bioactivities
             WHERE pchembl_value >= 7)                         AS potent_bioactivities,
            (SELECT COUNT(*) FROM bioactivities
             WHERE assay_variant_mutation IS NOT NULL)         AS bioactivities_with_mutation,
            (SELECT COUNT(DISTINCT assay_type)
             FROM bioactivities WHERE assay_type IS NOT NULL)  AS distinct_assay_types,
            (SELECT COUNT(DISTINCT document_journal)
             FROM bioactivities
             WHERE document_journal IS NOT NULL)               AS distinct_journals,

            -- ── Target enrichment (migration 0006) ───────────
            (SELECT COUNT(*) FROM targets
             WHERE tax_id IS NOT NULL)                         AS enriched_targets,
            (SELECT COUNT(DISTINCT gene_symbol)
             FROM target_components
             WHERE gene_symbol IS NOT NULL)                    AS distinct_genes,
            (SELECT COUNT(*) FROM target_xrefs
             WHERE xref_src_db IN ('PDB', 'PDBe'))             AS total_pdb_structures,

            -- ── Mechanism variants (migration 0007) ──────────
            (SELECT COUNT(*) FROM mechanisms
             WHERE variant_sequence IS NOT NULL)               AS mechanisms_with_variant,

            -- ── Clinical Trials (migration 0003) ─────────────
            (SELECT COUNT(*) FROM clinical_trials)             AS total_trials,
            (SELECT COUNT(DISTINCT chembl_id)
             FROM compound_clinical_trials)                    AS compounds_with_trials
    """)
    return row


# ============================================================
# Rotas — histopatologia (Owkin / TCGA)
# ============================================================

from owkin_routes import create_owkin_routes
create_owkin_routes(app, db_query, db_one, _resolve_compound_id)


# ============================================================
# Rotas — ensaios clínicos (ClinicalTrials.gov v2)
# ============================================================

from clinical_trials_routes import create_clinical_trials_routes
create_clinical_trials_routes(app, db_query, db_one, _resolve_compound_id)


# ============================================================
# Ponto de entrada
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)