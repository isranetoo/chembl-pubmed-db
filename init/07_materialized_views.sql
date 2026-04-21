-- ============================================================
-- Migration: views materializadas
-- Pré-computam as joins mais pesadas para consultas instantâneas.
--
-- Views criadas:
--   mv_compound_profile    — composto + ADMET + resumo clínico
--   mv_compound_articles   — composto + artigos (1 linha por artigo)
--   mv_compound_full       — tudo junto numa linha por composto (JSON)
--
-- Para atualizar após novo populate:
--   REFRESH MATERIALIZED VIEW CONCURRENTLY mv_compound_profile;
--   REFRESH MATERIALIZED VIEW CONCURRENTLY mv_compound_articles;
--   REFRESH MATERIALIZED VIEW CONCURRENTLY mv_compound_full;
--   -- ou usar o script: python refresh.py
-- ============================================================


-- ============================================================
-- 1. mv_compound_profile
--    Uma linha por composto com ADMET + contagens + fase clínica máxima.
--    Útil para ranking, filtros e comparações entre compostos.
-- ============================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_compound_profile AS
SELECT
    c.id                                                AS compound_id,
    c.chembl_id,
    c.name,
    c.molecular_formula,
    c.mol_weight,
    c.smiles,

    -- ADMET
    a.alogp,
    a.cx_logp,
    a.cx_logd,
    a.psa,
    a.hbd,
    a.hba,
    a.rtb,
    a.heavy_atoms,
    a.aromatic_rings,
    a.mw_freebase,
    a.qed_weighted,
    a.num_ro5_violations,
    a.num_alerts,
    a.ro3_pass,
    a.molecular_species,

    -- Flags de druglikeness (calculados inline)
    (a.num_ro5_violations = 0)                          AS lipinski_pass,
    (COALESCE(a.rtb,  0) <= 10
     AND COALESCE(a.psa, 0) <= 140)                    AS veber_pass,
    (COALESCE(a.num_alerts, 1) = 0)                    AS pains_free,

    -- Mecanismos: lista de action_types distintos
    (SELECT STRING_AGG(DISTINCT m.action_type, ', '
                       ORDER BY m.action_type)
     FROM mechanisms m
     WHERE m.compound_id = c.id
       AND m.action_type IS NOT NULL)                   AS action_types,

    (SELECT STRING_AGG(DISTINCT m.mechanism_of_action, ' | '
                       ORDER BY m.mechanism_of_action)
     FROM mechanisms m
     WHERE m.compound_id = c.id
       AND m.mechanism_of_action IS NOT NULL)           AS mechanisms_summary,

    -- Indicações: contagens por fase
    (SELECT COUNT(*)        FROM indications i WHERE i.compound_id = c.id)
                                                        AS total_indications,
    (SELECT COUNT(*) FILTER (WHERE i.max_phase >= 4)
     FROM indications i WHERE i.compound_id = c.id)    AS approved_indications,
    (SELECT MAX(i.max_phase)
     FROM indications i WHERE i.compound_id = c.id)    AS max_clinical_phase,

    -- Artigos: contagem e ano mais recente
    (SELECT COUNT(*)
     FROM article_compounds ac WHERE ac.compound_id = c.id)
                                                        AS total_articles,
    (SELECT MAX(ar.pub_year)
     FROM article_compounds ac
     JOIN articles ar ON ar.id = ac.article_id
     WHERE ac.compound_id = c.id)                      AS latest_article_year,

    NOW()                                               AS refreshed_at

FROM compounds        c
LEFT JOIN admet_properties a ON a.compound_id = c.id
ORDER BY c.name
WITH DATA;

-- Índices para buscas comuns sobre o profile
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_profile_id
    ON mv_compound_profile(compound_id);

CREATE INDEX IF NOT EXISTS idx_mv_profile_chembl
    ON mv_compound_profile(chembl_id);

CREATE INDEX IF NOT EXISTS idx_mv_profile_qed
    ON mv_compound_profile(qed_weighted DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_mv_profile_phase
    ON mv_compound_profile(max_clinical_phase DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_mv_profile_name
    ON mv_compound_profile(name);


-- ============================================================
-- 2. mv_compound_articles
--    Uma linha por (composto, artigo) com abstract e MeSH inline.
--    Útil para busca e listagem de literatura por composto.
-- ============================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_compound_articles AS
SELECT
    c.id                                    AS compound_id,
    c.chembl_id,
    c.name                                  AS compound_name,

    ar.id                                   AS article_id,
    ar.pmid,
    ar.title,
    ar.journal,
    ar.pub_year,
    ar.doi,
    LEFT(ar.abstract, 500)                  AS abstract_preview,
    ar.mesh_terms,
    ar.pub_types,
    ar.keywords,

    -- Snippet do abstract para exibição rápida
    LEFT(ar.abstract, 200)                  AS abstract_snippet,

    NOW()                                   AS refreshed_at

FROM compounds          c
JOIN article_compounds  ac ON ac.compound_id = c.id
JOIN articles           ar ON ar.id = ac.article_id
ORDER BY c.name, ar.pub_year DESC NULLS LAST
WITH DATA;

CREATE INDEX IF NOT EXISTS idx_mv_articles_compound
    ON mv_compound_articles(compound_id);

CREATE INDEX IF NOT EXISTS idx_mv_articles_chembl
    ON mv_compound_articles(chembl_id);

CREATE INDEX IF NOT EXISTS idx_mv_articles_year
    ON mv_compound_articles(pub_year DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_mv_articles_pmid
    ON mv_compound_articles(pmid);


-- ============================================================
-- 3. mv_compound_full
--    Uma linha por composto com TUDO em JSONB.
--    Ideal para exportação, APIs e consultas que precisam
--    de todos os dados sem múltiplos JOINs.
-- ============================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_compound_full AS
SELECT
    c.id                                        AS compound_id,
    c.chembl_id,
    c.name,
    c.molecular_formula,
    c.mol_weight,
    c.smiles,
    c.inchi_key,

    -- ADMET como objeto JSON
    TO_JSONB(a) - 'id' - 'compound_id' - 'created_at'
                                                AS admet,

    -- Indicações aprovadas (array JSON)
    (SELECT JSONB_AGG(JSONB_BUILD_OBJECT(
        'mesh_heading', i.mesh_heading,
        'efo_term',     i.efo_term,
        'max_phase',    i.max_phase
     ) ORDER BY i.max_phase DESC NULLS LAST)
     FROM indications i
     WHERE i.compound_id = c.id
       AND i.max_phase >= 4)                    AS approved_indications,

    -- Todas as indicações (array JSON)
    (SELECT JSONB_AGG(JSONB_BUILD_OBJECT(
        'mesh_heading', i.mesh_heading,
        'efo_term',     i.efo_term,
        'max_phase',    i.max_phase
     ) ORDER BY i.max_phase DESC NULLS LAST)
     FROM indications i
     WHERE i.compound_id = c.id)               AS all_indications,

    -- Mecanismos (array JSON)
    (SELECT JSONB_AGG(JSONB_BUILD_OBJECT(
        'mechanism_of_action', m.mechanism_of_action,
        'action_type',         m.action_type,
        'target_name',         m.target_name,
        'direct_interaction',  m.direct_interaction
     ))
     FROM mechanisms m
     WHERE m.compound_id = c.id)               AS mechanisms,

    -- Artigos (array JSON, ordenado por ano desc)
    (SELECT JSONB_AGG(JSONB_BUILD_OBJECT(
        'pmid',     ar.pmid,
        'title',    ar.title,
        'journal',  ar.journal,
        'pub_year', ar.pub_year,
        'doi',      ar.doi,
        'abstract', LEFT(ar.abstract, 300)
     ) ORDER BY ar.pub_year DESC NULLS LAST)
     FROM article_compounds ac
     JOIN articles ar ON ar.id = ac.article_id
     WHERE ac.compound_id = c.id)              AS articles,

    NOW()                                       AS refreshed_at

FROM compounds          c
LEFT JOIN admet_properties a ON a.compound_id = c.id
ORDER BY c.name
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_full_id
    ON mv_compound_full(compound_id);

CREATE INDEX IF NOT EXISTS idx_mv_full_chembl
    ON mv_compound_full(chembl_id);

CREATE INDEX IF NOT EXISTS idx_mv_full_name
    ON mv_compound_full(name);

-- GIN para buscas dentro dos arrays JSON
CREATE INDEX IF NOT EXISTS idx_mv_full_indications
    ON mv_compound_full USING GIN (approved_indications);

CREATE INDEX IF NOT EXISTS idx_mv_full_mechanisms
    ON mv_compound_full USING GIN (mechanisms);


-- ============================================================
-- Função de refresh única — atualiza as 3 views em sequência
--
-- Uso:
--   SELECT refresh_materialized_views();
--
-- CONCURRENTLY permite leituras durante o refresh (sem lock).
-- Requer índice UNIQUE em cada view (já criados acima).
-- ============================================================

CREATE OR REPLACE FUNCTION refresh_materialized_views()
RETURNS TABLE (view_name TEXT, duration_ms NUMERIC)
LANGUAGE plpgsql AS $$
DECLARE
    t0 TIMESTAMPTZ;
BEGIN
    t0 := clock_timestamp();
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_compound_profile;
    RETURN QUERY SELECT 'mv_compound_profile'::TEXT,
        ROUND(EXTRACT(EPOCH FROM (clock_timestamp() - t0)) * 1000, 0);

    t0 := clock_timestamp();
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_compound_articles;
    RETURN QUERY SELECT 'mv_compound_articles'::TEXT,
        ROUND(EXTRACT(EPOCH FROM (clock_timestamp() - t0)) * 1000, 0);

    t0 := clock_timestamp();
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_compound_full;
    RETURN QUERY SELECT 'mv_compound_full'::TEXT,
        ROUND(EXTRACT(EPOCH FROM (clock_timestamp() - t0)) * 1000, 0);
END;
$$;


-- ============================================================
-- Exemplos de uso
-- ============================================================

-- Perfil de todos os compostos ordenados por QED (druglikeness)
--   SELECT chembl_id, name, qed_weighted, lipinski_pass, veber_pass,
--          total_indications, approved_indications, total_articles
--   FROM mv_compound_profile
--   ORDER BY qed_weighted DESC NULLS LAST;

-- Artigos do Ibuprofen
--   SELECT title, journal, pub_year, abstract_snippet
--   FROM mv_compound_articles
--   WHERE compound_name ILIKE '%ibuprofen%'
--   ORDER BY pub_year DESC;

-- Dados completos do Imatinib em JSON
--   SELECT * FROM mv_compound_full WHERE chembl_id = 'CHEMBL941';

-- Compostos com indicação de câncer aprovados
--   SELECT name, approved_indications
--   FROM mv_compound_full
--   WHERE approved_indications @> '[{"mesh_heading": "Neoplasms"}]';

-- Atualizar após um novo populate:
--   SELECT * FROM refresh_materialized_views();