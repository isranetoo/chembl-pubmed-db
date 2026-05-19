"""
global_trials_routes.py — Página global de Clinical Trials
==========================================================

Endpoints cross-composto que listam e agregam a tabela `clinical_trials`
inteira (não apenas trials de 1 chembl_id). Pareados com a página
`/trials` no frontend, com filtros por sponsor, indicação, fase, status
e análise de endpoints primários.

Integração no api.py:

    from global_trials_routes import create_global_trials_routes
    create_global_trials_routes(app, db_query, db_one)
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Optional

from fastapi import Query
from psycopg2.errors import UndefinedTable

from schemas import (
    EndpointAnalysisResponse,
    EndpointBucket,
    Page,
    SponsorAggItem,
    ConditionAggItem,
    TrialGlobalListItem,
    TrialsGlobalStats,
)


# Padrões de endpoints clínicos clássicos — busca case-insensitive em
# `primary_endpoint`. A ordem importa: padrões mais específicos primeiro
# para evitar dupla contagem (cada trial conta no primeiro bucket que casa).
_ENDPOINT_PATTERNS: list[tuple[str, str, str]] = [
    # (regex, key, label legível)
    (r"progression[- ]free survival|\bpfs\b",       "pfs",       "Progression-Free Survival (PFS)"),
    (r"overall survival|\bos\b(?![a-z])",            "os",        "Overall Survival (OS)"),
    (r"disease[- ]free survival|\bdfs\b",            "dfs",       "Disease-Free Survival (DFS)"),
    (r"event[- ]free survival|\befs\b",              "efs",       "Event-Free Survival (EFS)"),
    (r"objective response rate|\borr\b",             "orr",       "Objective Response Rate (ORR)"),
    (r"complete response|\bcr\b",                    "cr",        "Complete Response (CR)"),
    (r"partial response|\bpr\b(?![a-z])",            "pr",        "Partial Response (PR)"),
    (r"duration of response|\bdor\b",                "dor",       "Duration of Response (DoR)"),
    (r"time to progression|\bttp\b",                 "ttp",       "Time to Progression (TTP)"),
    (r"minimal residual disease|\bmrd\b",            "mrd",       "Minimal Residual Disease (MRD)"),
    (r"recurrence[- ]free",                          "rfs",       "Recurrence-Free Survival"),
    (r"pathologic(al)? complete response|\bpcr\b",   "pcr",       "Pathologic Complete Response (pCR)"),
    (r"maximum tolerated dose|\bmtd\b",              "mtd",       "Maximum Tolerated Dose (MTD)"),
    (r"dose[- ]limiting toxicit",                    "dlt",       "Dose-Limiting Toxicities (DLTs)"),
    (r"\bauc\b|area under (the )?curve",             "auc",       "AUC / Pharmacokinetics"),
    (r"\bcmax\b|peak concentration",                 "cmax",      "Cmax / Pharmacokinetics"),
    (r"adverse event|safety|tolerab",                "safety",    "Safety / Adverse Events"),
    (r"quality of life|\bqol\b|\bqlq\b",             "qol",       "Quality of Life (QoL)"),
    (r"pain|\bvas\b score",                          "pain",      "Pain / VAS"),
    (r"hba1c|glycated h[ae]moglobin",                "hba1c",     "HbA1c"),
    (r"blood pressure|systolic|diastolic",           "bp",        "Blood Pressure"),
    (r"\bldl\b|\bhdl\b|cholesterol|triglyceride",    "lipids",    "Lipid panel"),
    (r"viral load|hiv[- ]rna|hcv[- ]rna",            "viral",     "Viral Load"),
    (r"recurr",                                      "recurrence","Recurrence"),
    (r"remission",                                   "remission", "Remission"),
    (r"mortality|death rate",                        "mortality", "Mortality"),
]

_STOPWORDS = {
    "the", "a", "an", "of", "in", "and", "or", "to", "for", "by", "from",
    "with", "on", "at", "is", "as", "be", "are", "was", "were", "this",
    "that", "after", "before", "between", "change", "rate", "level", "score",
    "time", "number", "percentage", "percent", "during", "up", "down", "vs",
    "study", "treatment", "patients", "participants", "subjects", "baseline",
    "weeks", "days", "months", "years", "hours",
}


def _normalize_phrase_tokens(text: str) -> list[str]:
    """Tokenização barata: lowercase, descarta stopwords e palavras
    muito curtas. Útil pra top-phrases."""
    words = re.findall(r"[a-zA-Z][a-zA-Z\-]+", (text or "").lower())
    return [w for w in words if len(w) >= 3 and w not in _STOPWORDS]


def create_global_trials_routes(app, db_query, db_one):
    """Registra os endpoints globais de Clinical Trials."""

    def _trials_exist() -> bool:
        """Retorna True se a tabela clinical_trials existe — proteção
        contra ambientes onde a migration 0003 ainda não rodou."""
        try:
            db_one("SELECT 1 FROM clinical_trials LIMIT 1")
            return True
        except UndefinedTable:
            return False
        except Exception as exc:
            if "does not exist" in str(exc).lower():
                return False
            raise

    # ── 1. Lista global paginada com filtros ─────────────────────────

    @app.get(
        "/trials",
        tags=["clinical-trials"],
        summary="Lista global de ensaios clínicos com filtros",
        response_model=Page[TrialGlobalListItem],
    )
    def list_trials(
        q:           Optional[str] = Query(None, description="Busca em título, sponsor e condições (ILIKE)"),
        status:      Optional[str] = Query(None, description="ex: RECRUITING, COMPLETED"),
        phase:       Optional[str] = Query(None, description="ex: PHASE2, PHASE3"),
        sponsor:     Optional[str] = Query(None, description="Filtro parcial por sponsor (ILIKE)"),
        condition:   Optional[str] = Query(None, description="Filtro por condição/indicação (ILIKE em qualquer item do array)"),
        study_type:  Optional[str] = Query(None, description="INTERVENTIONAL | OBSERVATIONAL | EXPANDED_ACCESS"),
        min_start:   Optional[str] = Query(None, description="Data início mínima (YYYY-MM-DD)"),
        max_start:   Optional[str] = Query(None, description="Data início máxima (YYYY-MM-DD)"),
        sort_by:     str           = Query("start_date", description="start_date | enrollment | nct_id"),
        sort_order:  str           = Query("desc", description="asc | desc"),
        page:        int           = Query(1,  ge=1),
        size:        int           = Query(20, ge=1, le=100),
    ):
        if not _trials_exist():
            return {"page": page, "size": size, "total": 0, "pages": 0, "items": []}

        valid_sorts = {
            "start_date": "ct.start_date",
            "enrollment": "ct.enrollment",
            "nct_id":     "ct.nct_id",
        }
        order_col = valid_sorts.get(sort_by, "ct.start_date")
        order_dir = "DESC" if sort_order.lower() == "desc" else "ASC"

        where = ["1=1"]
        params: list = []

        if q:
            where.append("""(
                ct.title ILIKE %s
                OR ct.sponsor ILIKE %s
                OR EXISTS (
                    SELECT 1 FROM unnest(ct.conditions) c
                    WHERE c ILIKE %s
                )
            )""")
            like = f"%{q}%"
            params += [like, like, like]
        if status:
            where.append("ct.status = %s::trial_status")
            params.append(status.upper())
        if phase:
            where.append("%s = ANY(ct.phases::text[])")
            params.append(phase.upper())
        if sponsor:
            where.append("ct.sponsor ILIKE %s")
            params.append(f"%{sponsor}%")
        if condition:
            where.append("EXISTS (SELECT 1 FROM unnest(ct.conditions) c WHERE c ILIKE %s)")
            params.append(f"%{condition}%")
        if study_type:
            where.append("ct.study_type = %s::trial_study_type")
            params.append(study_type.upper())
        if min_start:
            where.append("ct.start_date >= %s::date")
            params.append(min_start)
        if max_start:
            where.append("ct.start_date <= %s::date")
            params.append(max_start)

        where_sql = " AND ".join(where)

        count_row = db_one(
            f"SELECT COUNT(*) AS total FROM clinical_trials ct WHERE {where_sql}",
            params,
        )
        total = (count_row or {}).get("total", 0)
        pages = (total + size - 1) // size if total else 0

        items = db_query(
            f"""
            SELECT
                ct.nct_id,
                ct.title,
                ct.status::text                    AS status,
                ct.phases::text[]                  AS phases,
                ct.conditions,
                ct.interventions,
                ct.sponsor,
                ct.enrollment,
                ct.start_date::text                AS start_date,
                ct.primary_completion_date::text   AS primary_completion_date,
                ct.locations_count,
                ct.study_type::text                AS study_type,
                ct.primary_endpoint,
                COALESCE(linked.chembl_ids, ARRAY[]::text[]) AS chembl_ids,
                COALESCE(linked.compounds,  ARRAY[]::text[]) AS compounds
            FROM clinical_trials ct
            LEFT JOIN LATERAL (
                SELECT
                    array_agg(DISTINCT cct.chembl_id ORDER BY cct.chembl_id) AS chembl_ids,
                    array_agg(DISTINCT c.name        ORDER BY c.name)        AS compounds
                FROM compound_clinical_trials cct
                LEFT JOIN compounds c ON c.chembl_id = cct.chembl_id
                WHERE cct.nct_id = ct.nct_id
            ) linked ON TRUE
            WHERE {where_sql}
            ORDER BY {order_col} {order_dir} NULLS LAST, ct.nct_id
            LIMIT %s OFFSET %s
            """,
            params + [size, (page - 1) * size],
        )

        return {
            "page":  page,
            "size":  size,
            "total": total,
            "pages": pages,
            "items": items,
        }

    # ── 2. Stats globais ─────────────────────────────────────────────

    @app.get(
        "/trials/stats",
        tags=["clinical-trials"],
        summary="Estatísticas globais de trials",
        response_model=TrialsGlobalStats,
    )
    def trials_stats():
        if not _trials_exist():
            return {}

        base = db_one("""
            SELECT
                COUNT(*)                                                          AS total_trials,
                COUNT(*) FILTER (WHERE status = 'RECRUITING')                     AS recruiting_trials,
                COUNT(*) FILTER (WHERE status = 'COMPLETED')                      AS completed_trials,
                COUNT(*) FILTER (WHERE 'PHASE3' = ANY(phases))                    AS phase3_trials,
                COUNT(*) FILTER (WHERE 'PHASE4' = ANY(phases))                    AS phase4_trials,
                COUNT(*) FILTER (WHERE study_type = 'INTERVENTIONAL')             AS interventional,
                COUNT(*) FILTER (WHERE study_type = 'OBSERVATIONAL')              AS observational,
                COUNT(DISTINCT sponsor) FILTER (WHERE sponsor IS NOT NULL)        AS unique_sponsors,
                (SELECT COUNT(DISTINCT c) FROM clinical_trials, unnest(conditions) c
                 WHERE c IS NOT NULL)                                             AS unique_conditions,
                (SELECT COUNT(DISTINCT chembl_id) FROM compound_clinical_trials)  AS distinct_compounds_with_trials,
                MAX(start_date)::text                                             AS latest_trial_start
            FROM clinical_trials
        """) or {}

        by_status_rows = db_query("""
            SELECT status::text AS status, COUNT(*) AS n
            FROM clinical_trials
            WHERE status IS NOT NULL
            GROUP BY status
            ORDER BY n DESC
        """)
        by_phase_rows = db_query("""
            SELECT phase, COUNT(*) AS n
            FROM (
                SELECT unnest(phases)::text AS phase FROM clinical_trials
            ) sub
            WHERE phase IS NOT NULL
            GROUP BY phase
            ORDER BY n DESC
        """)

        return {
            **base,
            "by_status": {r["status"]: r["n"] for r in by_status_rows},
            "by_phase":  {r["phase"]:  r["n"] for r in by_phase_rows},
        }

    # ── 3. Top sponsors ──────────────────────────────────────────────

    @app.get(
        "/trials/sponsors",
        tags=["clinical-trials"],
        summary="Top sponsors por número de trials",
        response_model=Page[SponsorAggItem],
    )
    def trials_sponsors(
        q:    Optional[str] = Query(None, description="Filtro ILIKE no nome"),
        page: int = Query(1,  ge=1),
        size: int = Query(20, ge=1, le=100),
    ):
        if not _trials_exist():
            return {"page": page, "size": size, "total": 0, "pages": 0, "items": []}

        where = ["sponsor IS NOT NULL"]
        params: list = []
        if q:
            where.append("sponsor ILIKE %s")
            params.append(f"%{q}%")
        where_sql = " AND ".join(where)

        count_row = db_one(
            f"""
            SELECT COUNT(*) AS total FROM (
                SELECT sponsor FROM clinical_trials WHERE {where_sql} GROUP BY sponsor
            ) s
            """,
            params,
        )
        total = (count_row or {}).get("total", 0)
        pages = (total + size - 1) // size if total else 0

        items = db_query(
            f"""
            SELECT
                sponsor,
                COUNT(*)                                              AS trial_count,
                COUNT(*) FILTER (WHERE status = 'RECRUITING')         AS recruiting_trials,
                COUNT(*) FILTER (WHERE 'PHASE3' = ANY(phases))        AS phase3_trials,
                COUNT(*) FILTER (WHERE 'PHASE4' = ANY(phases))        AS phase4_trials
            FROM clinical_trials
            WHERE {where_sql}
            GROUP BY sponsor
            ORDER BY trial_count DESC, sponsor
            LIMIT %s OFFSET %s
            """,
            params + [size, (page - 1) * size],
        )

        return {"page": page, "size": size, "total": total, "pages": pages, "items": items}

    # ── 4. Top conditions ────────────────────────────────────────────

    @app.get(
        "/trials/conditions",
        tags=["clinical-trials"],
        summary="Top condições/indicações por número de trials",
        response_model=Page[ConditionAggItem],
    )
    def trials_conditions(
        q:    Optional[str] = Query(None, description="Filtro ILIKE"),
        page: int = Query(1,  ge=1),
        size: int = Query(30, ge=1, le=100),
    ):
        if not _trials_exist():
            return {"page": page, "size": size, "total": 0, "pages": 0, "items": []}

        where = ["condition IS NOT NULL", "condition <> ''"]
        params: list = []
        if q:
            where.append("condition ILIKE %s")
            params.append(f"%{q}%")
        where_sql = " AND ".join(where)

        count_row = db_one(
            f"""
            SELECT COUNT(*) AS total FROM (
                SELECT condition
                FROM (SELECT unnest(conditions) AS condition FROM clinical_trials) c
                WHERE {where_sql}
                GROUP BY condition
            ) sub
            """,
            params,
        )
        total = (count_row or {}).get("total", 0)
        pages = (total + size - 1) // size if total else 0

        items = db_query(
            f"""
            SELECT condition, COUNT(*) AS trial_count
            FROM (SELECT unnest(conditions) AS condition FROM clinical_trials) c
            WHERE {where_sql}
            GROUP BY condition
            ORDER BY trial_count DESC, condition
            LIMIT %s OFFSET %s
            """,
            params + [size, (page - 1) * size],
        )

        return {"page": page, "size": size, "total": total, "pages": pages, "items": items}

    # ── 5. Análise de endpoints ──────────────────────────────────────

    @app.get(
        "/trials/endpoints/analyze",
        tags=["clinical-trials"],
        summary="Análise de primary_endpoints — buckets clínicos comuns",
        response_model=EndpointAnalysisResponse,
    )
    def analyze_endpoints(
        condition: Optional[str] = Query(None, description="Filtra trials pela condição (ILIKE)"),
        sponsor:   Optional[str] = Query(None, description="Filtra por sponsor (ILIKE)"),
        phase:     Optional[str] = Query(None, description="Filtra por fase"),
        sample_examples: int = Query(3, ge=0, le=10, description="NCTs amostrais por bucket"),
    ):
        """
        Classifica `primary_endpoint` em buckets clínicos clássicos
        (OS, PFS, ORR, MTD, AUC, safety, QoL, etc.) usando regex
        case-insensitive. Cada trial cai no PRIMEIRO bucket que casar
        (sem dupla contagem). Também retorna top phrases (tokens
        frequentes) pra revelar padrões fora dos buckets pré-definidos.
        """
        if not _trials_exist():
            return {"total_with_endpoint": 0, "buckets": [], "top_phrases": []}

        where = ["primary_endpoint IS NOT NULL", "primary_endpoint <> ''"]
        params: list = []
        if condition:
            where.append("EXISTS (SELECT 1 FROM unnest(conditions) c WHERE c ILIKE %s)")
            params.append(f"%{condition}%")
        if sponsor:
            where.append("sponsor ILIKE %s")
            params.append(f"%{sponsor}%")
        if phase:
            where.append("%s = ANY(phases::text[])")
            params.append(phase.upper())
        where_sql = " AND ".join(where)

        rows = db_query(
            f"""
            SELECT nct_id, primary_endpoint
            FROM clinical_trials
            WHERE {where_sql}
            """,
            params,
        )

        buckets: dict[str, dict] = {
            key: {"key": key, "label": label, "regex": re.compile(regex, re.I),
                  "matches": 0, "examples": []}
            for regex, key, label in _ENDPOINT_PATTERNS
        }
        unmatched: list[str] = []

        for r in rows:
            ep = r.get("primary_endpoint") or ""
            matched = False
            for regex, key, _ in _ENDPOINT_PATTERNS:
                if buckets[key]["regex"].search(ep):
                    buckets[key]["matches"] += 1
                    if len(buckets[key]["examples"]) < sample_examples:
                        buckets[key]["examples"].append(r["nct_id"])
                    matched = True
                    break
            if not matched:
                unmatched.append(ep)

        # Top phrases (tokens) dos endpoints não classificados — surfaces
        # padrões custom de cada indicação
        token_counter: Counter[str] = Counter()
        for ep in unmatched:
            token_counter.update(_normalize_phrase_tokens(ep))
        top_phrases = [
            {"phrase": w, "count": c}
            for w, c in token_counter.most_common(20)
        ]

        output_buckets = [
            EndpointBucket(
                pattern=key,
                label=b["label"],
                matches=b["matches"],
                examples=b["examples"],
            )
            for key, b in buckets.items()
            if b["matches"] > 0
        ]
        output_buckets.sort(key=lambda x: -x.matches)

        return {
            "total_with_endpoint": len(rows),
            "buckets":             output_buckets,
            "top_phrases":         top_phrases,
        }
