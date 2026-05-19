"""
owkin_routes.py — Endpoints de Histopatologia (Owkin) para o DrugXpert
======================================================================

Registra endpoints diretamente no app FastAPI usando as mesmas funções
db_query/db_one do api.py, mantendo compatibilidade total com o pool
de conexões existente.

INTEGRAÇÃO (2 linhas no api.py):

    from owkin_routes import create_owkin_routes
    create_owkin_routes(app, db_query, db_one, _resolve_compound_id)

Adicione essas linhas logo antes do bloco `if __name__ == "__main__"`.
"""


def create_owkin_routes(app, db_query, db_one, _resolve_compound_id):
    """
    Registra todos os endpoints de histopatologia no app FastAPI.

    Args:
        app: instância FastAPI
        db_query: função db_query do api.py
        db_one: função db_one do api.py
        _resolve_compound_id: função do api.py que retorna UUID ou 404
    """
    from typing import Optional
    from fastapi import Query, HTTPException
    from psycopg2.errors import UndefinedTable

    _MIGRATION_HINT = (
        "Tabelas Owkin ausentes — rode `alembic upgrade head` no banco "
        "(ou aplique manualmente database/init/08_owkin_histopathology.sql)."
    )

    def _safe_query(sql, params=None, default=None):
        """db_query() resiliente: se as tabelas Owkin ainda não foram
        criadas (banco existente sem a migration 0008 aplicada), retorna
        `default` em vez de propagar UndefinedTable → 500."""
        try:
            return db_query(sql, params)
        except UndefinedTable:
            return default if default is not None else []
        except Exception as exc:
            # Outras exceções de DB podem ser quirks de connection state;
            # se a mensagem indica tabela ausente, trate igual.
            if "does not exist" in str(exc).lower():
                return default if default is not None else []
            raise

    def _safe_one(sql, params=None):
        try:
            return db_one(sql, params)
        except UndefinedTable:
            return None
        except Exception as exc:
            if "does not exist" in str(exc).lower():
                return None
            raise

    # Features-chave monitoradas pelo DrugXpert (subset das ~56 do Owkin)
    KEY_FEATURES = [
        "count_cancer_cell", "global_density_cancer_cell", "mean_area_cancer_cell",
        "count_lymphocytes", "global_density_lymphocytes",
        "density_lymphocytes_in_tumor", "density_lymphocytes_in_tumor_core",
        "density_lymphocytes_in_stroma_in_tumor_core", "tils_diffusivity",
        "count_fibroblasts", "global_density_fibroblasts", "density_fibroblasts_in_tumor",
        "count_neutrophils", "global_density_neutrophils",
        "count_plasmocytes", "global_density_plasmocytes",
        "count_eosinophils", "global_density_eosinophils",
        "average_co_occurrence_cancer_cell_lymphocytes_rad_20.0um",
        "average_co_occurrence_cancer_cell_fibroblasts_rad_20.0um",
        "area_tumor", "area_tumor_core", "area_stroma_in_tumor_core",
    ]

    # ── 1. Coortes TCGA de um composto ───────────────────────────────

    @app.get(
        "/compounds/{chembl_id}/histopathology",
        tags=["histopatologia"],
        summary="Coortes TCGA e TME de um composto",
    )
    def compound_histopathology(chembl_id: str):
        """
        Retorna as coortes TCGA mapeadas a um composto via suas indicações
        oncológicas, junto com as estatísticas TME de cada coorte.
        """
        compound_id = _resolve_compound_id(chembl_id)

        cohorts = _safe_query("""
            SELECT DISTINCT
                itm.tcga_cohort,
                tcd.cancer_name,
                i.mesh_heading AS indication,
                itm.disease_keyword AS match_keyword
            FROM indications i
            JOIN indication_tcga_map itm ON itm.indication_id = i.id
            JOIN tcga_cohort_dictionary tcd ON tcd.tcga_cohort = itm.tcga_cohort
            WHERE i.compound_id = %s
            ORDER BY itm.tcga_cohort
        """, (compound_id,), default=[])

        if not cohorts:
            return {
                "chembl_id": chembl_id.upper(),
                "message": (
                    "Nenhuma coorte TCGA mapeada para este composto. "
                    "Execute POST /histopathology/map-indications primeiro."
                ),
                "cohorts": [],
            }

        # Enriquecer cada coorte com resumo TME
        enriched = []
        for c in cohorts:
            stats = _safe_query("""
                SELECT feature, mean, std
                FROM owkin_cohort_stats
                WHERE tcga_cohort = %s
            """, (c["tcga_cohort"],), default=[])

            tme_summary = {}
            for s in stats:
                tme_summary[s["feature"]] = {
                    "mean": float(s["mean"]) if s["mean"] else None,
                    "std": float(s["std"]) if s["std"] else None,
                }

            enriched.append({
                **c,
                "tme_features_cached": len(stats),
                "tme_summary": tme_summary,
            })

        return {
            "chembl_id": chembl_id.upper(),
            "total_cohorts": len(enriched),
            "cohorts": enriched,
        }

    # ── 2. Dicionário de coortes ─────────────────────────────────────

    @app.get(
        "/histopathology/cohorts",
        tags=["histopatologia"],
        summary="Dicionário de coortes TCGA",
    )
    def list_tcga_cohorts():
        rows = _safe_query("""
            SELECT tcga_cohort, cancer_name, keywords
            FROM tcga_cohort_dictionary
            ORDER BY tcga_cohort
        """, default=[])
        return {"total": len(rows), "cohorts": rows}

    # ── 3. Estatísticas TME de uma coorte ────────────────────────────

    @app.get(
        "/histopathology/cohorts/{tcga_cohort}/tme",
        tags=["histopatologia"],
        summary="Estatísticas TME de uma coorte TCGA",
    )
    def cohort_tme_stats(
        tcga_cohort: str,
        feature: Optional[str] = Query(
            None, description="Filtrar por feature (ex: tils_diffusivity)"
        ),
    ):
        cohort = tcga_cohort.upper()

        sql = """
            SELECT feature, mean, std, min, max, p25, p50, p75,
                   fetched_at::text
            FROM owkin_cohort_stats
            WHERE tcga_cohort = %s
        """
        params = [cohort]

        if feature:
            sql += " AND feature = %s"
            params.append(feature)

        sql += " ORDER BY feature"
        stats = _safe_query(sql, params, default=[])

        if feature and not stats:
            raise HTTPException(
                404,
                detail=f"Feature '{feature}' não encontrada para {cohort}.",
            )

        # Converter Decimal → float
        for s in stats:
            for k in ["mean", "std", "min", "max", "p25", "p50", "p75"]:
                if s.get(k) is not None:
                    s[k] = float(s[k])

        return {
            "tcga_cohort": cohort,
            "total_features": len(stats),
            "stats": stats,
        }

    # ── 4. Top slides de uma coorte ──────────────────────────────────

    @app.get(
        "/histopathology/cohorts/{tcga_cohort}/slides",
        tags=["histopatologia"],
        summary="Top slides ranqueados por feature",
    )
    def cohort_top_slides(
        tcga_cohort: str,
        feature: str = Query("tils_diffusivity", description="Feature para ranking"),
        limit: int = Query(10, ge=1, le=100),
    ):
        cohort = tcga_cohort.upper()

        slides = _safe_query("""
            SELECT slide_id, value, rank_in_cohort AS rank, fetched_at::text
            FROM owkin_slides
            WHERE tcga_cohort = %s AND feature = %s
            ORDER BY rank_in_cohort ASC
            LIMIT %s
        """, (cohort, feature, limit), default=[])

        for s in slides:
            if s.get("value") is not None:
                s["value"] = float(s["value"])

        return {
            "tcga_cohort": cohort,
            "ranked_by": feature,
            "total": len(slides),
            "slides": slides,
        }

    # ── 5. Resumo TME comparativo ────────────────────────────────────

    @app.get(
        "/histopathology/summary",
        tags=["histopatologia"],
        summary="Resumo TME de todas as coortes",
    )
    def tme_summary():
        rows = _safe_query("SELECT * FROM v_tme_summary ORDER BY tcga_cohort", default=[])

        for row in rows:
            for k, v in row.items():
                if v is not None and k != "tcga_cohort":
                    row[k] = float(v)

        return {"total_cohorts": len(rows), "summary": rows}

    # ── 6. Auto-mapeamento de indicações ─────────────────────────────

    @app.post(
        "/histopathology/map-indications",
        tags=["histopatologia"],
        summary="Auto-mapear indicações para coortes TCGA",
    )
    def trigger_indication_mapping():
        """
        Percorre todas as indicações e mapeia via keywords para coortes TCGA.
        Deve ser chamado após popular novas indicações.
        """
        indications = _safe_query("SELECT id, mesh_heading FROM indications", default=[])
        cohort_kws = _safe_query(
            "SELECT tcga_cohort, keywords FROM tcga_cohort_dictionary",
            default=[],
        )
        if not cohort_kws:
            raise HTTPException(503, detail=_MIGRATION_HINT)

        mapped = 0
        for ind in indications:
            heading = (ind.get("mesh_heading") or "").lower()
            if not heading:
                continue

            for ckw in cohort_kws:
                for kw in ckw["keywords"]:
                    if kw.lower() in heading:
                        db_query("""
                            INSERT INTO indication_tcga_map
                                (indication_id, tcga_cohort, disease_keyword,
                                 match_type)
                            VALUES (%s, %s, %s, 'auto')
                            ON CONFLICT (indication_id, tcga_cohort)
                            DO NOTHING
                        """, (ind["id"], ckw["tcga_cohort"], kw))
                        mapped += 1
                        break

        return {
            "status": "ok",
            "mapped": mapped,
            "total_indications": len(indications),
        }

    # ── 7. Features disponíveis ──────────────────────────────────────

    @app.get(
        "/histopathology/features",
        tags=["histopatologia"],
        summary="Features histômicas monitoradas",
    )
    def available_features():
        return {
            "total": len(KEY_FEATURES),
            "features": KEY_FEATURES,
        }

    # ── 8. Stats da integração Owkin ─────────────────────────────────

    @app.get(
        "/histopathology/stats",
        tags=["histopatologia"],
        summary="Estatísticas da integração Owkin",
    )
    def histopathology_stats():
        row = _safe_one("""
            SELECT
                (SELECT COUNT(DISTINCT tcga_cohort)
                 FROM indication_tcga_map)          AS mapped_cohorts,
                (SELECT COUNT(*)
                 FROM indication_tcga_map)          AS total_mappings,
                (SELECT COUNT(DISTINCT tcga_cohort)
                 FROM owkin_cohort_stats)            AS cohorts_with_tme_data,
                (SELECT COUNT(*)
                 FROM owkin_cohort_stats)            AS cached_features,
                (SELECT COUNT(*)
                 FROM owkin_slides)                  AS cached_slides
        """)
        if row is None:
            return {
                "mapped_cohorts": 0,
                "total_mappings": 0,
                "cohorts_with_tme_data": 0,
                "cached_features": 0,
                "cached_slides": 0,
                "warning": _MIGRATION_HINT,
            }
        return row
