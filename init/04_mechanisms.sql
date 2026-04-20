-- ============================================================
-- Migration: mecanismos de ação
-- Fonte: endpoint /mechanism do ChEMBL
-- ============================================================

CREATE TABLE mechanisms (
    id                  UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    mec_id              INTEGER UNIQUE NOT NULL,  -- PK do ChEMBL

    compound_id         UUID    NOT NULL REFERENCES compounds(id) ON DELETE CASCADE,

    -- Alvo (FK opcional — o alvo pode não estar na tabela targets)
    target_id           UUID    REFERENCES targets(id) ON DELETE SET NULL,
    target_chembl_id    TEXT,   -- guardado mesmo quando target não está no banco
    target_name         TEXT,   -- desnormalizado para consultas rápidas

    -- Mecanismo
    mechanism_of_action TEXT,   -- ex: "Cyclooxygenase inhibitor"
    action_type         TEXT,   -- INHIBITOR | AGONIST | ANTAGONIST | BLOCKER | ...

    -- Flags booleanos do ChEMBL
    direct_interaction  BOOLEAN,  -- interage diretamente com o alvo?
    disease_efficacy    BOOLEAN,  -- relevante para eficácia terapêutica?

    -- Comentários livres
    mechanism_comment   TEXT,
    selectivity_comment TEXT,
    binding_site_comment TEXT,

    created_at          TIMESTAMP DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_mec_compound    ON mechanisms(compound_id);
CREATE INDEX idx_mec_target      ON mechanisms(target_id);
CREATE INDEX idx_mec_action_type ON mechanisms(action_type);

-- ============================================================
-- Views
-- ============================================================

-- Visão completa: composto + mecanismo + alvo
CREATE OR REPLACE VIEW v_mechanisms AS
SELECT
    c.name                  AS compound,
    c.chembl_id             AS compound_chembl_id,
    m.mechanism_of_action,
    m.action_type,
    m.target_name,
    m.target_chembl_id,
    m.direct_interaction,
    m.disease_efficacy,
    m.mechanism_comment
FROM mechanisms m
JOIN compounds  c ON c.id = m.compound_id
ORDER BY c.name, m.action_type;

-- Contagem de action_types por composto
CREATE OR REPLACE VIEW v_action_type_summary AS
SELECT
    c.name                          AS compound,
    m.action_type,
    COUNT(*)                        AS total,
    STRING_AGG(m.target_name, ', '
        ORDER BY m.target_name)     AS targets
FROM mechanisms m
JOIN compounds  c ON c.id = m.compound_id
WHERE m.action_type IS NOT NULL
GROUP BY c.name, m.action_type
ORDER BY c.name, total DESC;

-- Distribuição geral de action_types no banco
CREATE OR REPLACE VIEW v_action_type_distribution AS
SELECT
    action_type,
    COUNT(DISTINCT compound_id)     AS compounds,
    COUNT(*)                        AS total_entries
FROM mechanisms
WHERE action_type IS NOT NULL
GROUP BY action_type
ORDER BY total_entries DESC;