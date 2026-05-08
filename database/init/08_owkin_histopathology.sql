-- ============================================================================
-- 08_owkin_histopathology.sql
-- Integração com Owkin Pathology Explorer — dados histopatológicos do TCGA
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. Mapeamento indicação → coorte TCGA
--    Conecta as indicações dos compostos (tabela indications) às coortes
--    disponíveis no Owkin Pathology Explorer.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS indication_tcga_map (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    indication_id   UUID REFERENCES indications(id) ON DELETE CASCADE,
    tcga_cohort     TEXT NOT NULL,          -- ex: TCGA_BRCA, TCGA_LUAD
    disease_keyword TEXT NOT NULL,          -- palavra-chave usada no match
    match_type      TEXT DEFAULT 'manual',  -- 'manual' | 'auto' | 'fuzzy'
    created_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(indication_id, tcga_cohort)
);

CREATE INDEX IF NOT EXISTS idx_itm_indication ON indication_tcga_map(indication_id);
CREATE INDEX IF NOT EXISTS idx_itm_cohort     ON indication_tcga_map(tcga_cohort);

-- ---------------------------------------------------------------------------
-- 2. Dados de coorte agregados (cache de cohort_description)
--    Estatísticas por coorte e feature histômica — evita chamadas repetidas.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS owkin_cohort_stats (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tcga_cohort TEXT NOT NULL,
    feature     TEXT NOT NULL,
    mean        NUMERIC,
    std         NUMERIC,
    min         NUMERIC,
    max         NUMERIC,
    p25         NUMERIC,
    p50         NUMERIC,
    p75         NUMERIC,
    fetched_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE(tcga_cohort, feature)
);

CREATE INDEX IF NOT EXISTS idx_ocs_cohort ON owkin_cohort_stats(tcga_cohort);

-- ---------------------------------------------------------------------------
-- 3. Dados de slides individuais (cache de filter_slides)
--    Top slides por feature de cada coorte — usados pra visualização.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS owkin_slides (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tcga_cohort  TEXT NOT NULL,
    slide_id     TEXT NOT NULL,
    feature      TEXT NOT NULL,
    value        NUMERIC,
    rank_in_cohort INTEGER,
    fetched_at   TIMESTAMP DEFAULT NOW(),
    UNIQUE(tcga_cohort, slide_id, feature)
);

CREATE INDEX IF NOT EXISTS idx_os_cohort  ON owkin_slides(tcga_cohort);
CREATE INDEX IF NOT EXISTS idx_os_slide   ON owkin_slides(slide_id);

-- ---------------------------------------------------------------------------
-- 4. Seed: mapeamento padrão de keywords de indicação → coorte TCGA
--    Usado pelo owkin_client.py para auto-mapear indicações existentes.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tcga_cohort_dictionary (
    tcga_cohort TEXT PRIMARY KEY,
    cancer_name TEXT NOT NULL,
    keywords    TEXT[] NOT NULL  -- array de keywords para fuzzy match
);

INSERT INTO tcga_cohort_dictionary (tcga_cohort, cancer_name, keywords) VALUES
    ('TCGA_ACC',  'Adrenocortical Carcinoma',              ARRAY['adrenocortical', 'adrenal cortex', 'adrenal carcinoma']),
    ('TCGA_BLCA', 'Bladder Urothelial Carcinoma',          ARRAY['bladder', 'urothelial', 'urinary bladder']),
    ('TCGA_BRCA', 'Breast Invasive Carcinoma',             ARRAY['breast', 'mammary', 'breast cancer']),
    ('TCGA_CESC', 'Cervical Squamous Cell Carcinoma',      ARRAY['cervical', 'cervix', 'cervical cancer']),
    ('TCGA_CHOL', 'Cholangiocarcinoma',                    ARRAY['cholangiocarcinoma', 'bile duct', 'biliary']),
    ('TCGA_COAD', 'Colon Adenocarcinoma',                  ARRAY['colon', 'colorectal', 'colonic', 'bowel']),
    ('TCGA_DLBC', 'Diffuse Large B-cell Lymphoma',         ARRAY['lymphoma', 'dlbcl', 'b-cell lymphoma', 'diffuse large']),
    ('TCGA_ESCA', 'Esophageal Carcinoma',                  ARRAY['esophageal', 'oesophageal', 'esophagus']),
    ('TCGA_HNSC', 'Head and Neck Squamous Cell Carcinoma', ARRAY['head and neck', 'oral cavity', 'pharynx', 'larynx', 'oropharyngeal']),
    ('TCGA_KICH', 'Kidney Chromophobe',                    ARRAY['kidney chromophobe', 'chromophobe renal']),
    ('TCGA_KIRC', 'Kidney Renal Clear Cell Carcinoma',     ARRAY['renal clear cell', 'kidney clear cell', 'renal cell carcinoma', 'kidney cancer']),
    ('TCGA_KIRP', 'Kidney Renal Papillary Cell Carcinoma', ARRAY['renal papillary', 'kidney papillary']),
    ('TCGA_LIHC', 'Liver Hepatocellular Carcinoma',        ARRAY['liver', 'hepatocellular', 'hepatic', 'hcc']),
    ('TCGA_LUAD', 'Lung Adenocarcinoma',                   ARRAY['lung adenocarcinoma', 'lung cancer', 'non-small cell lung', 'nsclc']),
    ('TCGA_LUSC', 'Lung Squamous Cell Carcinoma',          ARRAY['lung squamous', 'squamous cell lung']),
    ('TCGA_MESO', 'Mesothelioma',                          ARRAY['mesothelioma', 'pleural mesothelioma']),
    ('TCGA_OV',   'Ovarian Serous Cystadenocarcinoma',     ARRAY['ovarian', 'ovary', 'ovarian cancer']),
    ('TCGA_PAAD', 'Pancreatic Adenocarcinoma',             ARRAY['pancreatic', 'pancreas', 'pancreatic cancer']),
    ('TCGA_PRAD', 'Prostate Adenocarcinoma',               ARRAY['prostate', 'prostatic']),
    ('TCGA_READ', 'Rectum Adenocarcinoma',                 ARRAY['rectal', 'rectum', 'rectal cancer']),
    ('TCGA_SARC', 'Sarcoma',                               ARRAY['sarcoma', 'soft tissue sarcoma']),
    ('TCGA_STAD', 'Stomach Adenocarcinoma',                ARRAY['stomach', 'gastric', 'gastric cancer']),
    ('TCGA_THCA', 'Thyroid Carcinoma',                     ARRAY['thyroid', 'thyroid cancer']),
    ('TCGA_THYM', 'Thymoma',                               ARRAY['thymoma', 'thymic']),
    ('TCGA_UCEC', 'Uterine Corpus Endometrial Carcinoma',  ARRAY['endometrial', 'uterine', 'uterine cancer']),
    ('TCGA_UCS',  'Uterine Carcinosarcoma',                ARRAY['carcinosarcoma', 'uterine carcinosarcoma'])
ON CONFLICT (tcga_cohort) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 5. Views de conveniência
-- ---------------------------------------------------------------------------

-- Compostos com indicações oncológicas que têm mapeamento TCGA
CREATE OR REPLACE VIEW v_compounds_with_histopathology AS
SELECT DISTINCT
    c.chembl_id,
    c.name AS compound_name,
    i.mesh_heading AS indication,
    itm.tcga_cohort,
    tcd.cancer_name AS tcga_cancer_name
FROM compounds c
JOIN indications i  ON i.compound_id = c.id
JOIN indication_tcga_map itm ON itm.indication_id = i.id
JOIN tcga_cohort_dictionary tcd ON tcd.tcga_cohort = itm.tcga_cohort;

-- Resumo TME por coorte (features-chave pré-agregadas)
CREATE OR REPLACE VIEW v_tme_summary AS
SELECT
    tcga_cohort,
    MAX(CASE WHEN feature = 'tils_diffusivity' THEN mean END)                    AS tils_diffusivity_mean,
    MAX(CASE WHEN feature = 'global_density_lymphocytes' THEN mean END)           AS lymphocyte_density_mean,
    MAX(CASE WHEN feature = 'global_density_fibroblasts' THEN mean END)           AS fibroblast_density_mean,
    MAX(CASE WHEN feature = 'global_density_cancer_cell' THEN mean END)           AS cancer_cell_density_mean,
    MAX(CASE WHEN feature = 'global_density_neutrophils' THEN mean END)           AS neutrophil_density_mean,
    MAX(CASE WHEN feature = 'density_lymphocytes_in_tumor' THEN mean END)         AS tils_in_tumor_mean,
    MAX(CASE WHEN feature = 'area_tumor' THEN mean END)                           AS tumor_area_mean,
    MAX(CASE WHEN feature = 'count_cancer_cell' THEN mean END)                    AS cancer_cell_count_mean
FROM owkin_cohort_stats
GROUP BY tcga_cohort;
