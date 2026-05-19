-- ============================================================
-- Migration: ensaios clínicos (ClinicalTrials.gov v2)
-- ------------------------------------------------------------
-- Camada de "Clinical Status" — cacheia trials da CT.gov por composto.
-- Idempotente: pode rodar do zero ou sobre banco já populado.
--
-- FK de compound_clinical_trials.chembl_id aponta para compounds(chembl_id)
-- em vez do compounds(id) UUID que o resto do schema usa, porque a chave
-- natural já é única e o módulo é consultado sempre por chembl_id.
-- ============================================================

-- ------------------------------------------------------------
-- Enums (idempotentes)
-- ------------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE trial_status AS ENUM (
        'NOT_YET_RECRUITING', 'RECRUITING', 'ENROLLING_BY_INVITATION',
        'ACTIVE_NOT_RECRUITING', 'SUSPENDED', 'TERMINATED', 'COMPLETED',
        'WITHDRAWN', 'UNKNOWN', 'APPROVED_FOR_MARKETING',
        'AVAILABLE', 'NO_LONGER_AVAILABLE', 'TEMPORARILY_NOT_AVAILABLE',
        'WITHHELD'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE trial_phase AS ENUM (
        'EARLY_PHASE1', 'PHASE1', 'PHASE2', 'PHASE3', 'PHASE4', 'NA'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE trial_study_type AS ENUM (
        'INTERVENTIONAL', 'OBSERVATIONAL', 'EXPANDED_ACCESS'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE intervention_match_method AS ENUM (
        'exact_name', 'synonym', 'normalized', 'fuzzy', 'manual'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;


-- ------------------------------------------------------------
-- Função de trigger genérica para updated_at
-- ------------------------------------------------------------
-- CREATE OR REPLACE é idempotente; se outra migration já criou a função
-- com o mesmo corpo, isso é no-op semântico.
CREATE OR REPLACE FUNCTION handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ------------------------------------------------------------
-- Tabela: clinical_trials
-- ------------------------------------------------------------
-- PK natural nct_id (já é único na CT.gov) evita um UUID surrogate
-- que não traz benefício aqui.
CREATE TABLE IF NOT EXISTS clinical_trials (
    nct_id                    TEXT PRIMARY KEY,
    title                     TEXT,
    status                    trial_status,
    phases                    trial_phase[]      DEFAULT '{}',
    conditions                TEXT[]             DEFAULT '{}',
    interventions             TEXT[]             DEFAULT '{}',
    sponsor                   TEXT,
    enrollment                INTEGER,
    start_date                DATE,
    primary_completion_date   DATE,
    locations_count           INTEGER            DEFAULT 0,
    study_type                trial_study_type,
    primary_endpoint          TEXT,
    -- Payload original da CT.gov, guardado para re-extração futura sem
    -- precisar voltar à API. Indexado em GIN abaixo para queries jsonb.
    raw                       JSONB,
    last_synced_at            TIMESTAMPTZ        DEFAULT NOW(),
    created_at                TIMESTAMPTZ        DEFAULT NOW(),
    updated_at                TIMESTAMPTZ        DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_clinical_trials_updated_at ON clinical_trials;
CREATE TRIGGER trg_clinical_trials_updated_at
BEFORE UPDATE ON clinical_trials
FOR EACH ROW EXECUTE FUNCTION handle_updated_at();


-- ------------------------------------------------------------
-- Tabela: compound_clinical_trials (junção)
-- ------------------------------------------------------------
-- intervention_name guarda o label original do CT.gov (ex: "Imatinib
-- Mesylate") antes da normalização — útil pra debugar matches.
CREATE TABLE IF NOT EXISTS compound_clinical_trials (
    chembl_id            TEXT NOT NULL
                              REFERENCES compounds(chembl_id) ON DELETE CASCADE,
    nct_id               TEXT NOT NULL
                              REFERENCES clinical_trials(nct_id) ON DELETE CASCADE,
    intervention_name    TEXT NOT NULL,
    match_method         intervention_match_method NOT NULL,
    match_confidence     NUMERIC(3,2) NOT NULL
                              CHECK (match_confidence BETWEEN 0 AND 1),
    created_at           TIMESTAMPTZ DEFAULT NOW(),
    updated_at           TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (chembl_id, nct_id)
);

DROP TRIGGER IF EXISTS trg_compound_clinical_trials_updated_at ON compound_clinical_trials;
CREATE TRIGGER trg_compound_clinical_trials_updated_at
BEFORE UPDATE ON compound_clinical_trials
FOR EACH ROW EXECUTE FUNCTION handle_updated_at();


-- ------------------------------------------------------------
-- Índices
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_clinical_trials_status
    ON clinical_trials(status);
CREATE INDEX IF NOT EXISTS idx_clinical_trials_sponsor
    ON clinical_trials(sponsor);
CREATE INDEX IF NOT EXISTS idx_clinical_trials_start_date
    ON clinical_trials(start_date DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_clinical_trials_phases_gin
    ON clinical_trials USING GIN (phases);
CREATE INDEX IF NOT EXISTS idx_clinical_trials_conditions_gin
    ON clinical_trials USING GIN (conditions);
CREATE INDEX IF NOT EXISTS idx_compound_clinical_trials_chembl
    ON compound_clinical_trials(chembl_id);


-- ------------------------------------------------------------
-- View agregada: v_compound_trials_summary
-- ------------------------------------------------------------
-- View regular (não materializada) — agregação por chembl_id é barata em
-- volumes esperados (<= 1000 trials/composto). Refresca de graça.
CREATE OR REPLACE VIEW v_compound_trials_summary AS
SELECT
    cct.chembl_id,
    COUNT(*)                                                         AS total_trials,
    COUNT(*) FILTER (WHERE ct.status = 'RECRUITING')                 AS recruiting_trials,
    COUNT(*) FILTER (WHERE ct.status = 'COMPLETED')                  AS completed_trials,
    COUNT(*) FILTER (WHERE 'PHASE3' = ANY(ct.phases))                AS phase3_trials,
    COUNT(*) FILTER (WHERE 'PHASE4' = ANY(ct.phases))                AS phase4_trials,
    COUNT(DISTINCT ct.sponsor) FILTER (WHERE ct.sponsor IS NOT NULL) AS unique_sponsors,
    MAX(ct.start_date)                                               AS latest_trial_start
FROM compound_clinical_trials cct
JOIN clinical_trials ct ON ct.nct_id = cct.nct_id
GROUP BY cct.chembl_id;


-- ------------------------------------------------------------
-- RLS: deliberadamente omitido
-- ------------------------------------------------------------
-- Este projeto roda Postgres direto (não Supabase). Não há auth.users
-- nem JWT — uma policy "select using (true)" seria decorativa. Quando
-- migrar pro Supabase, adicionar:
--   ALTER TABLE clinical_trials ENABLE ROW LEVEL SECURITY;
--   CREATE POLICY ct_read ON clinical_trials FOR SELECT USING (true);
--   (idem para compound_clinical_trials)
