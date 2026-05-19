-- ============================================================
-- Migration: enriquecimento de bioactivities
-- Fonte: endpoint /activity do ChEMBL (mesma requisição já feita
-- por fetch_bioactivities — sem chamada extra)
--
-- Adiciona ao registro de bioatividade:
--   - activity_id (PK do ChEMBL) → UPSERT idempotente
--   - pchembl_value → potência padronizada -log[molar]
--   - dados do ensaio (assay_chembl_id, type B/F/A/T/P, descrição)
--   - organismo + tax_id do alvo
--   - referência bibliográfica (document_*, year, journal)
--   - ligand efficiency (BEI / LE / LLE / SEI)
--   - flags de qualidade (data_validity_comment, potential_duplicate)
--   - variantes de assay (T315I e similares — essencial p/ resistência)
--
-- Idempotente: re-execução sobre banco já migrado é no-op.
-- ============================================================

-- ------------------------------------------------------------
-- bioactivities — colunas adicionais
-- ------------------------------------------------------------
ALTER TABLE bioactivities ADD COLUMN IF NOT EXISTS activity_id           BIGINT;
ALTER TABLE bioactivities ADD COLUMN IF NOT EXISTS pchembl_value         NUMERIC;
ALTER TABLE bioactivities ADD COLUMN IF NOT EXISTS standard_value        NUMERIC;
ALTER TABLE bioactivities ADD COLUMN IF NOT EXISTS standard_units        TEXT;

ALTER TABLE bioactivities ADD COLUMN IF NOT EXISTS assay_chembl_id       TEXT;
ALTER TABLE bioactivities ADD COLUMN IF NOT EXISTS assay_description     TEXT;
ALTER TABLE bioactivities ADD COLUMN IF NOT EXISTS assay_type            TEXT;     -- B|F|A|T|P|U
ALTER TABLE bioactivities ADD COLUMN IF NOT EXISTS bao_label             TEXT;

ALTER TABLE bioactivities ADD COLUMN IF NOT EXISTS target_organism       TEXT;
ALTER TABLE bioactivities ADD COLUMN IF NOT EXISTS target_tax_id         INTEGER;

ALTER TABLE bioactivities ADD COLUMN IF NOT EXISTS document_chembl_id    TEXT;
ALTER TABLE bioactivities ADD COLUMN IF NOT EXISTS document_journal      TEXT;
ALTER TABLE bioactivities ADD COLUMN IF NOT EXISTS document_year         INTEGER;

-- Ligand Efficiency Metrics:
--   bei  = Binding Efficiency Index   = pchembl / MW(kDa)
--   le   = Ligand Efficiency          = 1.37 * pchembl / heavy_atoms
--   lle  = Lipophilic LE              = pchembl - LogP
--   sei  = Surface Efficiency Index   = pchembl / PSA(100 Å²)
ALTER TABLE bioactivities ADD COLUMN IF NOT EXISTS bei                   NUMERIC;
ALTER TABLE bioactivities ADD COLUMN IF NOT EXISTS le                    NUMERIC;
ALTER TABLE bioactivities ADD COLUMN IF NOT EXISTS lle                   NUMERIC;
ALTER TABLE bioactivities ADD COLUMN IF NOT EXISTS sei                   NUMERIC;

ALTER TABLE bioactivities ADD COLUMN IF NOT EXISTS data_validity_comment TEXT;
ALTER TABLE bioactivities ADD COLUMN IF NOT EXISTS activity_comment      TEXT;
ALTER TABLE bioactivities ADD COLUMN IF NOT EXISTS potential_duplicate   BOOLEAN;

-- Variantes do alvo (mutações em estudos de resistência):
--   accession ex: P00519
--   mutation  ex: T315I, M351T (separados por vírgula se múltiplas)
ALTER TABLE bioactivities ADD COLUMN IF NOT EXISTS assay_variant_accession TEXT;
ALTER TABLE bioactivities ADD COLUMN IF NOT EXISTS assay_variant_mutation  TEXT;


-- ------------------------------------------------------------
-- UNIQUE parcial em activity_id
-- ------------------------------------------------------------
-- Linhas legadas (inseridas antes desta migration) têm activity_id NULL.
-- Um UNIQUE convencional permitiria múltiplos NULLs, mas índices em
-- Postgres tratam NULLs como distintos por padrão — o que é o que queremos:
--   - novas inserções com activity_id → ON CONFLICT DO UPDATE
--   - linhas antigas (NULL)           → coexistem sem violar a constraint
--
-- Usamos índice parcial para clareza de intenção (só ativa quando há valor).
CREATE UNIQUE INDEX IF NOT EXISTS ux_bioactivities_activity_id
    ON bioactivities (activity_id)
    WHERE activity_id IS NOT NULL;


-- ------------------------------------------------------------
-- Índices auxiliares para filtros frequentes
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_bioact_pchembl       ON bioactivities(pchembl_value);
CREATE INDEX IF NOT EXISTS idx_bioact_assay_type    ON bioactivities(assay_type);
CREATE INDEX IF NOT EXISTS idx_bioact_doc_year      ON bioactivities(document_year);
CREATE INDEX IF NOT EXISTS idx_bioact_variant_mut   ON bioactivities(assay_variant_mutation)
    WHERE assay_variant_mutation IS NOT NULL;


-- ============================================================
-- Views
-- ============================================================

-- Top atividades por potência: pChEMBL ≥ 7  ⇒  <100 nM (drug-like)
CREATE OR REPLACE VIEW v_top_potent_activities AS
SELECT
    c.chembl_id            AS compound_chembl_id,
    c.name                 AS compound,
    t.chembl_id            AS target_chembl_id,
    t.name                 AS target,
    b.target_organism,
    b.activity_type,
    b.standard_value,
    b.standard_units,
    b.pchembl_value,
    b.assay_type,
    b.assay_description,
    b.document_journal,
    b.document_year,
    b.bei, b.le, b.lle, b.sei,
    b.assay_variant_mutation
FROM bioactivities b
JOIN compounds c ON c.id = b.compound_id
JOIN targets   t ON t.id = b.target_id
WHERE b.pchembl_value IS NOT NULL
  AND b.pchembl_value >= 7
ORDER BY b.pchembl_value DESC NULLS LAST;
