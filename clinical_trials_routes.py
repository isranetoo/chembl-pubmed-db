"""
clinical_trials_routes.py — Endpoints de ensaios clínicos para o DrugXpert
=========================================================================

Camada "Clinical Status" do perfil do composto. Espelha o padrão de
owkin_routes.py: factory que recebe app + helpers do api.py e registra
as rotas.

Integração no api.py (2 linhas):

    from clinical_trials_routes import create_clinical_trials_routes
    create_clinical_trials_routes(
        app, db_query, db_one, _resolve_compound_id,
    )
"""

from __future__ import annotations

import logging

import requests
from fastapi import HTTPException, Query

from populate.clinicaltrials_client import sync_compound_trials
from populate.db import get_conn
from schemas import (
    SyncResponse,
    TrialKPIs,
    TrialRow,
    TrialsResponse,
)

log = logging.getLogger("clinical_trials_routes")


def create_clinical_trials_routes(app, db_query, db_one, _resolve_compound_id):
    """Registra os endpoints de Clinical Trials no app FastAPI."""

    # ── 1. GET trials cacheados ──────────────────────────────────────

    @app.get(
        "/compounds/{chembl_id}/trials",
        tags=["clinical-trials"],
        summary="Ensaios clínicos cacheados (CT.gov v2)",
        response_model=TrialsResponse,
    )
    def get_compound_trials(
        chembl_id: str,
        status:    str | None = Query(None, description="Filtrar por status (ex: RECRUITING)"),
        phase:     str | None = Query(None, description="Filtrar por fase (ex: PHASE3)"),
        limit:     int        = Query(50, ge=1, le=500),
    ):
        # _resolve_compound_id já retorna 404 quando não existe; descartamos o UUID.
        _resolve_compound_id(chembl_id)
        cid = chembl_id.upper()

        # KPIs vêm da view agregada. Composto sem nenhum sync ainda → COALESCE
        # zera tudo e a resposta sai 200 com total_trials=0 (requisito do spec).
        kpi_row = db_one(
            """
            SELECT
                COALESCE(total_trials,       0) AS total_trials,
                COALESCE(recruiting_trials,  0) AS recruiting_trials,
                COALESCE(completed_trials,   0) AS completed_trials,
                COALESCE(phase3_trials,      0) AS phase3_trials,
                COALESCE(phase4_trials,      0) AS phase4_trials,
                COALESCE(unique_sponsors,    0) AS unique_sponsors,
                latest_trial_start::text        AS latest_trial_start
            FROM v_compound_trials_summary
            WHERE chembl_id = %s
            """,
            (cid,),
        ) or {
            "total_trials": 0, "recruiting_trials": 0, "completed_trials": 0,
            "phase3_trials": 0, "phase4_trials": 0, "unique_sponsors": 0,
            "latest_trial_start": None,
        }

        rows = db_query(
            """
            SELECT
                ct.nct_id,
                ct.title,
                ct.status::text                     AS status,
                ct.phases::text[]                   AS phases,
                ct.conditions,
                ct.interventions,
                ct.sponsor,
                ct.enrollment,
                ct.start_date::text                 AS start_date,
                ct.primary_completion_date::text    AS primary_completion_date,
                ct.locations_count,
                ct.study_type::text                 AS study_type,
                ct.primary_endpoint,
                cct.intervention_name,
                cct.match_method::text              AS match_method,
                cct.match_confidence::float         AS match_confidence,
                ct.last_synced_at::text             AS last_synced_at
            FROM compound_clinical_trials cct
            JOIN clinical_trials ct ON ct.nct_id = cct.nct_id
            WHERE cct.chembl_id = %s
            ORDER BY cct.match_confidence DESC, ct.start_date DESC NULLS LAST
            """,
            (cid,),
        )

        # Filtros aplicados em Python — volume por composto é baixo
        # (ordens de centenas no pior caso). Evita complicar a query.
        if status:
            wanted = status.upper()
            rows = [r for r in rows if (r.get("status") or "") == wanted]
        if phase:
            wanted = phase.upper()
            rows = [r for r in rows if wanted in (r.get("phases") or [])]

        rows = rows[:limit]

        return {
            "chembl_id": cid,
            "kpis":      kpi_row,
            "trials":    rows,
        }

    # ── 2. POST sync ─────────────────────────────────────────────────

    @app.post(
        "/compounds/{chembl_id}/trials/sync",
        tags=["clinical-trials"],
        summary="Sincronizar trials a partir da CT.gov v2",
        response_model=SyncResponse,
    )
    def sync_trials(
        chembl_id: str,
        drug_name: str | None = Query(
            None,
            description="Nome a buscar na CT.gov. Omitido → usa compounds.name.",
        ),
    ):
        _resolve_compound_id(chembl_id)
        cid = chembl_id.upper()

        # Fallback pro nome canônico do composto se o caller não passou.
        name = drug_name
        if not name:
            row = db_one("SELECT name FROM compounds WHERE chembl_id = %s", (cid,))
            name = (row or {}).get("name")
        if not name:
            raise HTTPException(
                422,
                detail=(
                    f"Composto {cid} não tem 'name' utilizável e drug_name "
                    "não foi informado."
                ),
            )

        conn = get_conn()
        try:
            with conn.cursor() as cur:
                result = sync_compound_trials(cur, cid, name)
            conn.commit()
        except requests.RequestException as exc:
            conn.rollback()
            log.exception("ct.gov fetch failed for %s/%s", cid, name)
            raise HTTPException(
                502,
                detail=f"Falha consultando ClinicalTrials.gov: {exc}",
            ) from exc
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        return {
            "chembl_id":       cid,
            "drug_name":       name,
            "trials_fetched":  result["trials_fetched"],
            "trials_upserted": result["trials_upserted"],
            "links_created":   result["links_created"],
        }
