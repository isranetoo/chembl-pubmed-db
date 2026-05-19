-- ============================================================
-- Migration: enriquecimento clínico/regulatório de compounds
-- Fonte: endpoint /molecule/{id} do ChEMBL (mesma requisição
-- já feita por fetch_compound — sem chamada extra)
--
-- Inclui:
--   - novas colunas em compounds (fase clínica, aprovação, vias
--     de administração, flags regulatórios, USAN stem, InChI)
--   - tabela compound_synonyms (sinônimos com tipo: INN, BAN,
--     trade names, códigos de pesquisa)
--   - tabela compound_atc (classificação ATC da WHO, 5 níveis)
--
-- Idempotente: re-execução sobre banco já migrado é no-op.
-- ============================================================

-- ------------------------------------------------------------
-- compounds — colunas adicionais
-- ------------------------------------------------------------
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS max_phase            NUMERIC;
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS first_approval       INTEGER;
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS molecule_type        TEXT;
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS oral                 BOOLEAN;
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS parenteral           BOOLEAN;
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS topical              BOOLEAN;
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS black_box_warning    BOOLEAN;
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS withdrawn_flag       BOOLEAN;
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS withdrawn_reason     TEXT;
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS withdrawn_year       INTEGER;
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS withdrawn_country    TEXT;
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS withdrawn_class      TEXT;
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS prodrug              BOOLEAN;
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS natural_product      BOOLEAN;
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS therapeutic_flag     BOOLEAN;
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS first_in_class       BOOLEAN;
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS orphan               BOOLEAN;
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS chirality            INTEGER;
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS availability_type    INTEGER;
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS usan_stem            TEXT;
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS usan_stem_definition TEXT;
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS usan_year            INTEGER;
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS inchi                TEXT;
ALTER TABLE compounds ADD COLUMN IF NOT EXISTS np_likeness_score    NUMERIC;

-- Índices úteis para filtros comuns no frontend.
CREATE INDEX IF NOT EXISTS idx_compounds_max_phase
    ON compounds(max_phase);
CREATE INDEX IF NOT EXISTS idx_compounds_first_approval
    ON compounds(first_approval);
CREATE INDEX IF NOT EXISTS idx_compounds_molecule_type
    ON compounds(molecule_type);
CREATE INDEX IF NOT EXISTS idx_compounds_withdrawn
    ON compounds(withdrawn_flag) WHERE withdrawn_flag = TRUE;
CREATE INDEX IF NOT EXISTS idx_compounds_blackbox
    ON compounds(black_box_warning) WHERE black_box_warning = TRUE;


-- ------------------------------------------------------------
-- compound_synonyms — INN, BAN, USAN, trade names, research codes
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS compound_synonyms (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    compound_id  UUID NOT NULL REFERENCES compounds(id) ON DELETE CASCADE,
    synonym      TEXT NOT NULL,           -- ex: "Glamox", "Imatinib", "NSC-743414"
    syn_type     TEXT,                    -- INN | BAN | USAN | TRADE_NAME | RESEARCH_CODE | ATC | OTHER
    created_at   TIMESTAMP DEFAULT NOW(),
    UNIQUE (compound_id, synonym, syn_type)
);

CREATE INDEX IF NOT EXISTS idx_compound_synonyms_compound
    ON compound_synonyms(compound_id);
CREATE INDEX IF NOT EXISTS idx_compound_synonyms_lower
    ON compound_synonyms(LOWER(synonym));


-- ------------------------------------------------------------
-- compound_atc — classificação ATC (WHO Anatomical Therapeutic)
-- Cada composto pode ter múltiplos códigos ATC.
-- Estrutura hierárquica:
--   level1 (1 letra)  — sistema anatômico   (L = Antineoplásicos)
--   level2 (2 dígitos) — grupo terapêutico  (L01)
--   level3 (1 letra)  — subgrupo farmacológico
--   level4 (1 letra)  — subgrupo químico
--   level5 (2 dígitos) — substância química (L01EA01 = imatinib)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS compound_atc (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    compound_id          UUID NOT NULL REFERENCES compounds(id) ON DELETE CASCADE,
    level5               TEXT NOT NULL,         -- código completo ex: "L01EA01"
    level1               TEXT,
    level1_description   TEXT,
    level2               TEXT,
    level2_description   TEXT,
    level3               TEXT,
    level3_description   TEXT,
    level4               TEXT,
    level4_description   TEXT,
    created_at           TIMESTAMP DEFAULT NOW(),
    UNIQUE (compound_id, level5)
);

CREATE INDEX IF NOT EXISTS idx_compound_atc_compound  ON compound_atc(compound_id);
CREATE INDEX IF NOT EXISTS idx_compound_atc_level5    ON compound_atc(level5);
CREATE INDEX IF NOT EXISTS idx_compound_atc_level1    ON compound_atc(level1);


-- ============================================================
-- View de conveniência — perfil clínico/regulatório do composto
-- ============================================================
CREATE OR REPLACE VIEW v_compound_clinical AS
SELECT
    c.id,
    c.chembl_id,
    c.name,
    c.molecule_type,
    c.max_phase,
    CASE c.max_phase
        WHEN 4   THEN 'Approved'
        WHEN 3   THEN 'Phase 3'
        WHEN 2   THEN 'Phase 2'
        WHEN 1   THEN 'Phase 1'
        WHEN 0.5 THEN 'Early Phase 1'
        ELSE          'Preclinical / Unknown'
    END                                       AS phase_label,
    c.first_approval,
    c.oral, c.parenteral, c.topical,
    c.black_box_warning,
    c.withdrawn_flag, c.withdrawn_reason, c.withdrawn_year,
    c.prodrug, c.natural_product, c.first_in_class, c.orphan,
    c.usan_stem, c.usan_stem_definition
FROM compounds c;
