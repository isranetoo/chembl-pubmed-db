-- ============================================================
-- Migration: tabela de indicações terapêuticas
-- Relação doença/indicação → composto via ChEMBL drug_indication
-- ============================================================

CREATE TABLE indications (
    id           UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    drugind_id   INTEGER UNIQUE NOT NULL,  -- PK do ChEMBL, evita duplicatas
    compound_id  UUID    NOT NULL REFERENCES compounds(id) ON DELETE CASCADE,

    -- Vocabulário MeSH (Medical Subject Headings)
    mesh_id      TEXT,      -- ex: "D006261"
    mesh_heading TEXT,      -- ex: "Headache"

    -- Vocabulário EFO (Experimental Factor Ontology)
    efo_id       TEXT,      -- ex: "EFO:0003843"
    efo_term     TEXT,      -- ex: "headache"

    -- Fase clínica máxima atingida para esta indicação
    --   4    = aprovado
    --   3    = fase 3
    --   2    = fase 2
    --   1    = fase 1
    --   0.5  = early phase 1
    --  -1    = pré-clínico
    max_phase    NUMERIC,

    created_at   TIMESTAMP DEFAULT NOW()
);

-- Índices para buscas comuns
CREATE INDEX idx_ind_compound   ON indications(compound_id);
CREATE INDEX idx_ind_mesh       ON indications(mesh_heading);
CREATE INDEX idx_ind_efo        ON indications(efo_term);
CREATE INDEX idx_ind_max_phase  ON indications(max_phase);

-- ============================================================
-- Views de conveniência
-- ============================================================

-- Todos os compostos com suas indicações, fase legível
CREATE OR REPLACE VIEW v_indications AS
SELECT
    c.name                               AS compound,
    c.chembl_id,
    i.mesh_heading                       AS disease_mesh,
    i.efo_term                           AS disease_efo,
    i.max_phase,
    CASE i.max_phase
        WHEN  4   THEN 'Approved'
        WHEN  3   THEN 'Phase 3'
        WHEN  2   THEN 'Phase 2'
        WHEN  1   THEN 'Phase 1'
        WHEN  0.5 THEN 'Early Phase 1'
        ELSE           'Preclinical'
    END                                  AS phase_label
FROM indications i
JOIN compounds   c ON c.id = i.compound_id
ORDER BY i.max_phase DESC NULLS LAST, c.name, i.mesh_heading;

-- Apenas drogas aprovadas (max_phase = 4)
CREATE OR REPLACE VIEW v_approved_drugs AS
SELECT
    c.name         AS compound,
    c.chembl_id,
    i.mesh_heading AS disease,
    i.efo_term,
    i.mesh_id,
    i.efo_id
FROM indications i
JOIN compounds   c ON c.id = i.compound_id
WHERE i.max_phase >= 4
ORDER BY c.name, i.mesh_heading;

-- Quantas indicações aprovadas cada composto tem
CREATE OR REPLACE VIEW v_compounds_indication_count AS
SELECT
    c.name                                          AS compound,
    COUNT(*)                                        AS total_indications,
    COUNT(*) FILTER (WHERE i.max_phase >= 4)        AS approved,
    COUNT(*) FILTER (WHERE i.max_phase  = 3)        AS phase_3,
    COUNT(*) FILTER (WHERE i.max_phase  = 2)        AS phase_2
FROM compounds   c
LEFT JOIN indications i ON i.compound_id = c.id
GROUP BY c.name
ORDER BY approved DESC, total_indications DESC;