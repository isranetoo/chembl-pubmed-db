-- ============================================================
-- Migration: propriedades ADMET
-- Fonte: molecule_properties do endpoint /molecule/{id} do ChEMBL
-- Sem requisição extra — dados já retornados por fetch_compound
-- ============================================================

CREATE TABLE admet_properties (
    id                  UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    compound_id         UUID    UNIQUE NOT NULL
                                REFERENCES compounds(id) ON DELETE CASCADE,

    -- ── Lipofilia ──────────────────────────────────────────
    alogp               NUMERIC,   -- logP calculado (Wildman-Crippen)
    cx_logp             NUMERIC,   -- logP (ChemAxon)
    cx_logd             NUMERIC,   -- logD a pH 7.4 (ChemAxon)

    -- ── Solubilidade / pKa ─────────────────────────────────
    cx_most_apka        NUMERIC,   -- pKa ácido mais forte
    cx_most_bpka        NUMERIC,   -- pKa básico mais forte
    molecular_species   TEXT,      -- ACID | BASE | NEUTRAL | ZWITTERION

    -- ── Tamanho e forma ────────────────────────────────────
    mw_freebase         NUMERIC,   -- MW da base livre
    mw_monoisotopic     NUMERIC,   -- MW monoisotópico
    heavy_atoms         INTEGER,   -- número de átomos pesados
    aromatic_rings      INTEGER,   -- número de anéis aromáticos
    rtb                 INTEGER,   -- rotatable bonds

    -- ── Regras de druglikeness ─────────────────────────────
    -- Lipinski (Rule of 5)
    hbd                 INTEGER,   -- H-bond donors
    hbd_lipinski        INTEGER,   -- H-bond donors (Lipinski)
    hba                 INTEGER,   -- H-bond acceptors
    hba_lipinski        INTEGER,   -- H-bond acceptors (Lipinski)
    psa                 NUMERIC,   -- polar surface area (Å²)
    num_ro5_violations  INTEGER,   -- violações da Rule of 5

    -- Veber: rtb ≤ 10 AND psa ≤ 140
    -- (calculado via view abaixo)

    -- Rule of 3 (fragment-like)
    ro3_pass            TEXT,       -- Y | N

    -- ── Qualidade ──────────────────────────────────────────
    qed_weighted        NUMERIC,   -- QED drug-likeness score (0-1)
    num_alerts          INTEGER,   -- structural alerts (PAINS etc.)

    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_admet_compound ON admet_properties(compound_id);

-- ============================================================
-- Views
-- ============================================================

-- Perfil ADMET completo com flags de druglikeness calculados
CREATE OR REPLACE VIEW v_admet_profile AS
SELECT
    c.name                                          AS compound,
    c.chembl_id,

    -- Lipofilia
    a.alogp, a.cx_logp, a.cx_logd,

    -- Tamanho
    a.mw_freebase, a.heavy_atoms, a.aromatic_rings, a.rtb,

    -- Polaridade
    a.psa, a.hbd, a.hba,

    -- pKa / espécie
    a.cx_most_apka, a.cx_most_bpka, a.molecular_species,

    -- Druglikeness
    a.qed_weighted, a.num_alerts, a.num_ro5_violations, a.ro3_pass,

    -- Flags calculados
    CASE
        WHEN a.num_ro5_violations = 0 THEN true
        ELSE false
    END                                             AS lipinski_pass,

    CASE
        WHEN (a.rtb IS NULL OR a.rtb <= 10)
         AND (a.psa IS NULL OR a.psa <= 140)        THEN true
        ELSE false
    END                                             AS veber_pass,

    CASE
        WHEN a.num_alerts IS NOT NULL
         AND a.num_alerts  = 0                      THEN true
        ELSE false
    END                                             AS pains_free

FROM admet_properties a
JOIN compounds        c ON c.id = a.compound_id
ORDER BY a.qed_weighted DESC NULLS LAST;


-- Ranking de druglikeness
CREATE OR REPLACE VIEW v_druglikeness_ranking AS
SELECT
    c.name                                      AS compound,
    ROUND(a.qed_weighted::numeric, 3)           AS qed,
    a.num_ro5_violations                        AS ro5_violations,
    a.num_alerts                                AS structural_alerts,
    a.alogp,
    a.psa,
    a.hbd,
    a.hba,
    a.rtb,
    CASE WHEN a.num_ro5_violations = 0
         THEN 'pass' ELSE 'fail' END            AS lipinski,
    CASE WHEN (a.rtb  IS NULL OR a.rtb  <= 10)
          AND (a.psa   IS NULL OR a.psa  <= 140)
         THEN 'pass' ELSE 'fail' END            AS veber
FROM admet_properties a
JOIN compounds        c ON c.id = a.compound_id
ORDER BY a.qed_weighted DESC NULLS LAST;