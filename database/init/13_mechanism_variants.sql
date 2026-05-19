-- ============================================================
-- Migration: variant_sequence em mechanisms
-- Fonte: endpoint /mechanism do ChEMBL (mesma requisição já feita
-- por fetch_mechanisms — sem chamada extra)
--
-- O campo variant_sequence descreve mutações associadas a um
-- mecanismo — essencial para entender resistência a drogas.
-- Exemplo: BCR-ABL T315I é refratário a imatinib mas responde
-- a ponatinib.
--
-- Armazenado como JSONB porque o ChEMBL retorna estrutura aninhada
-- (mutation, accession, isoform, organism, …) que pode variar.
-- ============================================================

ALTER TABLE mechanisms ADD COLUMN IF NOT EXISTS variant_sequence JSONB;

CREATE INDEX IF NOT EXISTS idx_mec_variant
    ON mechanisms((variant_sequence->>'mutation'))
    WHERE variant_sequence IS NOT NULL;


-- View: mecanismos com mutações específicas
CREATE OR REPLACE VIEW v_mechanism_variants AS
SELECT
    c.chembl_id                          AS compound_chembl_id,
    c.name                               AS compound,
    m.mechanism_of_action,
    m.action_type,
    m.target_chembl_id,
    m.target_name,
    m.variant_sequence ->> 'mutation'    AS mutation,
    m.variant_sequence ->> 'accession'   AS accession,
    m.variant_sequence ->> 'organism'    AS variant_organism,
    m.variant_sequence
FROM mechanisms m
JOIN compounds  c ON c.id = m.compound_id
WHERE m.variant_sequence IS NOT NULL;
