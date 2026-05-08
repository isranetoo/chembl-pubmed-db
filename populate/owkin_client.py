"""
owkin_client.py — Cliente Owkin Pathology Explorer para o DrugXpert
==================================================================

Integra dados histopatológicos do TCGA (via Owkin MCP) com o banco
farmacológico local. Responsável por:

1. Auto-mapear indicações dos compostos a coortes TCGA (via keywords)
2. Buscar e cachear estatísticas de microambiente tumoral por coorte
3. Buscar top slides por feature histômica
4. Fornecer dados prontos pra API e frontend

Dependências:
    - psycopg2 (via db.py)
    - requests (pra chamadas ao Owkin MCP — quando usado fora do Claude)

Nota: Este módulo é projetado para funcionar tanto como script standalone
(populate_owkin.py) quanto importado pela API FastAPI.
"""

import logging
from db import get_conn

logger = logging.getLogger("owkin_client")

# ── Features-chave para cache automático ──────────────────────────────────────
# Subset das ~56 features do Owkin que são mais relevantes para o DrugXpert.
# O populate busca estatísticas dessas features pra cada coorte mapeada.

KEY_FEATURES = [
    # Células tumorais
    "count_cancer_cell",
    "global_density_cancer_cell",
    "mean_area_cancer_cell",
    # Linfócitos (TILs)
    "count_lymphocytes",
    "global_density_lymphocytes",
    "density_lymphocytes_in_tumor",
    "density_lymphocytes_in_tumor_core",
    "density_lymphocytes_in_stroma_in_tumor_core",
    "tils_diffusivity",
    # Fibroblastos (estroma)
    "count_fibroblasts",
    "global_density_fibroblasts",
    "density_fibroblasts_in_tumor",
    # Neutrófilos
    "count_neutrophils",
    "global_density_neutrophils",
    # Plasmócitos
    "count_plasmocytes",
    "global_density_plasmocytes",
    # Eosinófilos
    "count_eosinophils",
    "global_density_eosinophils",
    # Co-ocorrência espacial
    "average_co_occurrence_cancer_cell_lymphocytes_rad_20.0um",
    "average_co_occurrence_cancer_cell_fibroblasts_rad_20.0um",
    # Regiões tumorais
    "area_tumor",
    "area_tumor_core",
    "area_stroma_in_tumor_core",
]

# ── Todas as coortes TCGA disponíveis no Owkin ────────────────────────────────
ALL_TCGA_COHORTS = [
    "TCGA_ACC", "TCGA_BLCA", "TCGA_BRCA", "TCGA_CESC", "TCGA_CHOL",
    "TCGA_COAD", "TCGA_DLBC", "TCGA_ESCA", "TCGA_HNSC", "TCGA_KICH",
    "TCGA_KIRC", "TCGA_KIRP", "TCGA_LIHC", "TCGA_LUAD", "TCGA_LUSC",
    "TCGA_MESO", "TCGA_OV",  "TCGA_PAAD", "TCGA_PRAD", "TCGA_READ",
    "TCGA_SARC", "TCGA_STAD", "TCGA_THCA", "TCGA_THYM", "TCGA_UCEC",
    "TCGA_UCS",
]


# ═══════════════════════════════════════════════════════════════════════════════
# 1. AUTO-MAPEAMENTO: indication → TCGA cohort
# ═══════════════════════════════════════════════════════════════════════════════

def auto_map_indications():
    """
    Percorre todas as indicações no banco e tenta mapeá-las a coortes TCGA
    usando as keywords do dicionário tcga_cohort_dictionary.

    Lógica: para cada indicação, verifica se alguma keyword de alguma coorte
    aparece no mesh_heading (case-insensitive). Se sim, cria o mapeamento
    na tabela indication_tcga_map.

    Returns:
        dict com contagens: {"mapped": int, "skipped": int, "total": int}
    """
    conn = get_conn()
    cur = conn.cursor()

    # Buscar todas as indicações
    cur.execute("SELECT id, mesh_heading FROM indications")
    indications = cur.fetchall()

    # Buscar o dicionário de keywords
    cur.execute("SELECT tcga_cohort, keywords FROM tcga_cohort_dictionary")
    cohort_keywords = cur.fetchall()

    mapped = 0
    skipped = 0

    for ind_id, mesh_heading in indications:
        if not mesh_heading:
            skipped += 1
            continue

        heading_lower = mesh_heading.lower()

        for tcga_cohort, keywords in cohort_keywords:
            for kw in keywords:
                if kw.lower() in heading_lower:
                    try:
                        cur.execute("""
                            INSERT INTO indication_tcga_map
                                (indication_id, tcga_cohort, disease_keyword, match_type)
                            VALUES (%s, %s, %s, 'auto')
                            ON CONFLICT (indication_id, tcga_cohort) DO NOTHING
                        """, (ind_id, tcga_cohort, kw))
                        mapped += 1
                    except Exception as e:
                        logger.warning(f"Erro mapeando {mesh_heading} → {tcga_cohort}: {e}")
                    break  # uma keyword bastou pra esse par

    conn.commit()
    cur.close()
    conn.close()

    result = {"mapped": mapped, "skipped": skipped, "total": len(indications)}
    logger.info(f"Auto-map concluído: {result}")
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 2. CACHE DE ESTATÍSTICAS: cohort_description → owkin_cohort_stats
# ═══════════════════════════════════════════════════════════════════════════════

def upsert_cohort_stats(tcga_cohort: str, feature: str, stats: dict):
    """
    Insere ou atualiza estatísticas de uma feature numa coorte.

    Args:
        tcga_cohort: ex: "TCGA_BRCA"
        feature: ex: "tils_diffusivity"
        stats: dict com keys "mean", "std", "min", "max", "25%", "50%", "75%"
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO owkin_cohort_stats
            (tcga_cohort, feature, mean, std, min, max, p25, p50, p75)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (tcga_cohort, feature)
        DO UPDATE SET
            mean = EXCLUDED.mean,
            std  = EXCLUDED.std,
            min  = EXCLUDED.min,
            max  = EXCLUDED.max,
            p25  = EXCLUDED.p25,
            p50  = EXCLUDED.p50,
            p75  = EXCLUDED.p75,
            fetched_at = NOW()
    """, (
        tcga_cohort, feature,
        stats.get("mean"), stats.get("std"),
        stats.get("min"), stats.get("max"),
        stats.get("25%"), stats.get("50%"), stats.get("75%"),
    ))

    conn.commit()
    cur.close()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 3. CACHE DE SLIDES: filter_slides → owkin_slides
# ═══════════════════════════════════════════════════════════════════════════════

def upsert_slide(tcga_cohort: str, slide_id: str, feature: str,
                 value: float, rank: int):
    """
    Insere ou atualiza um slide no cache local.

    Args:
        tcga_cohort: ex: "TCGA_LUAD"
        slide_id: ID do slide no TCGA
        feature: feature pela qual foi ranqueado
        value: valor da feature
        rank: posição no ranking (1 = maior valor)
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO owkin_slides
            (tcga_cohort, slide_id, feature, value, rank_in_cohort)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (tcga_cohort, slide_id, feature)
        DO UPDATE SET
            value = EXCLUDED.value,
            rank_in_cohort = EXCLUDED.rank_in_cohort,
            fetched_at = NOW()
    """, (tcga_cohort, slide_id, feature, value, rank))

    conn.commit()
    cur.close()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 4. CONSULTAS PARA A API
# ═══════════════════════════════════════════════════════════════════════════════

def get_cohorts_for_compound(chembl_id: str) -> list:
    """
    Retorna as coortes TCGA mapeadas para um composto via suas indicações.

    Returns:
        Lista de dicts: [{"tcga_cohort": str, "cancer_name": str,
                          "indication": str, "match_keyword": str}, ...]
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT
            itm.tcga_cohort,
            tcd.cancer_name,
            i.mesh_heading AS indication,
            itm.disease_keyword
        FROM compounds c
        JOIN indications i ON i.compound_id = c.id
        JOIN indication_tcga_map itm ON itm.indication_id = i.id
        JOIN tcga_cohort_dictionary tcd ON tcd.tcga_cohort = itm.tcga_cohort
        WHERE c.chembl_id = %s
        ORDER BY itm.tcga_cohort
    """, (chembl_id,))

    columns = ["tcga_cohort", "cancer_name", "indication", "match_keyword"]
    results = [dict(zip(columns, row)) for row in cur.fetchall()]

    cur.close()
    conn.close()
    return results


def get_tme_stats(tcga_cohort: str) -> list:
    """
    Retorna todas as estatísticas cacheadas para uma coorte.

    Returns:
        Lista de dicts com feature, mean, std, min, max, p25, p50, p75
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT feature, mean, std, min, max, p25, p50, p75, fetched_at
        FROM owkin_cohort_stats
        WHERE tcga_cohort = %s
        ORDER BY feature
    """, (tcga_cohort,))

    columns = ["feature", "mean", "std", "min", "max", "p25", "p50", "p75",
               "fetched_at"]
    results = [dict(zip(columns, row)) for row in cur.fetchall()]

    cur.close()
    conn.close()
    return results


def get_top_slides(tcga_cohort: str, feature: str, limit: int = 10) -> list:
    """
    Retorna os top slides de uma coorte ranqueados por uma feature.

    Returns:
        Lista de dicts: [{"slide_id": str, "value": float, "rank": int}, ...]
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT slide_id, value, rank_in_cohort, fetched_at
        FROM owkin_slides
        WHERE tcga_cohort = %s AND feature = %s
        ORDER BY rank_in_cohort ASC
        LIMIT %s
    """, (tcga_cohort, feature, limit))

    columns = ["slide_id", "value", "rank", "fetched_at"]
    results = [dict(zip(columns, row)) for row in cur.fetchall()]

    cur.close()
    conn.close()
    return results


def get_tme_summary_all() -> list:
    """
    Retorna o resumo TME de todas as coortes (via view v_tme_summary).
    Útil para o dashboard comparativo.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM v_tme_summary ORDER BY tcga_cohort")

    columns = [desc[0] for desc in cur.description]
    results = [dict(zip(columns, row)) for row in cur.fetchall()]

    cur.close()
    conn.close()
    return results


def get_cohort_dictionary() -> list:
    """Retorna o dicionário completo de coortes TCGA."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT tcga_cohort, cancer_name, keywords
        FROM tcga_cohort_dictionary
        ORDER BY tcga_cohort
    """)

    columns = ["tcga_cohort", "cancer_name", "keywords"]
    results = [dict(zip(columns, row)) for row in cur.fetchall()]

    cur.close()
    conn.close()
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# 5. SCRIPT DE POPULATE (quando rodado standalone)
# ═══════════════════════════════════════════════════════════════════════════════

def populate_owkin_data():
    """
    Pipeline completo de ingestão Owkin:
    1. Auto-mapeia indicações a coortes TCGA
    2. Para cada coorte mapeada, busca estatísticas das KEY_FEATURES

    NOTA: As chamadas ao Owkin MCP (cohort_description, filter_slides)
    devem ser feitas via Claude ou via API MCP diretamente.
    Este script prepara o banco e faz o mapeamento; as stats precisam
    ser inseridas via upsert_cohort_stats() após obter os dados do MCP.
    """
    logger.info("═" * 60)
    logger.info("OWKIN POPULATE — Início")
    logger.info("═" * 60)

    # Etapa 1: auto-map
    logger.info("Etapa 1/2: Auto-mapeamento indicações → TCGA...")
    map_result = auto_map_indications()
    logger.info(f"  Resultado: {map_result}")

    # Etapa 2: listar coortes mapeadas
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT tcga_cohort
        FROM indication_tcga_map
        ORDER BY tcga_cohort
    """)
    mapped_cohorts = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()

    logger.info(f"Etapa 2/2: {len(mapped_cohorts)} coortes mapeadas: "
                f"{mapped_cohorts}")
    logger.info("")
    logger.info("Para popular as estatísticas, use o Owkin MCP:")
    logger.info("  Para cada coorte, chame Owkin:cohort_description")
    logger.info("  com cada feature de KEY_FEATURES e salve via")
    logger.info("  owkin_client.upsert_cohort_stats()")
    logger.info("")
    logger.info("═" * 60)
    logger.info("OWKIN POPULATE — Fim")
    logger.info("═" * 60)

    return mapped_cohorts


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s │ %(name)s │ %(message)s",
        datefmt="%H:%M:%S",
    )
    populate_owkin_data()
