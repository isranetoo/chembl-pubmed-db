-- ============================================================
-- Schema: ChEMBL + PubMed local database
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ------------------------------------------------------------
-- ChEMBL: compostos
-- ------------------------------------------------------------
CREATE TABLE compounds (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chembl_id        TEXT UNIQUE NOT NULL,
    name             TEXT NOT NULL,
    molecular_formula TEXT,
    mol_weight       NUMERIC,
    smiles           TEXT,
    inchi_key        TEXT,
    alogp            NUMERIC,
    hbd              INTEGER,   -- hydrogen bond donors
    hba              INTEGER,   -- hydrogen bond acceptors
    psa              NUMERIC,   -- polar surface area
    ro5_violations   INTEGER,   -- Lipinski rule-of-5 violations
    created_at       TIMESTAMP DEFAULT NOW()
);

-- ------------------------------------------------------------
-- ChEMBL: alvos biologicos
-- ------------------------------------------------------------
CREATE TABLE targets (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chembl_id        TEXT UNIQUE NOT NULL,
    name             TEXT NOT NULL,
    type             TEXT,
    organism         TEXT,
    created_at       TIMESTAMP DEFAULT NOW()
);

-- ------------------------------------------------------------
-- ChEMBL: bioatividades (composto x alvo)
-- ------------------------------------------------------------
CREATE TABLE bioactivities (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    compound_id      UUID NOT NULL REFERENCES compounds(id) ON DELETE CASCADE,
    target_id        UUID NOT NULL REFERENCES targets(id)   ON DELETE CASCADE,
    activity_type    TEXT,    -- IC50, Ki, EC50...
    value            NUMERIC,
    units            TEXT,
    relation         TEXT,    -- =, <, >
    created_at       TIMESTAMP DEFAULT NOW()
);

-- ------------------------------------------------------------
-- PubMed: artigos
-- ------------------------------------------------------------
CREATE TABLE articles (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pmid             TEXT UNIQUE NOT NULL,
    title            TEXT,
    abstract         TEXT,
    authors          JSONB,   -- ["Autor A", "Autor B", ...]
    journal          TEXT,
    pub_year         INTEGER,
    doi              TEXT,
    created_at       TIMESTAMP DEFAULT NOW()
);

-- ------------------------------------------------------------
-- Relacao N:M — artigos <-> compostos
-- ------------------------------------------------------------
CREATE TABLE article_compounds (
    article_id       UUID NOT NULL REFERENCES articles(id)   ON DELETE CASCADE,
    compound_id      UUID NOT NULL REFERENCES compounds(id)  ON DELETE CASCADE,
    mention_type     TEXT DEFAULT 'research',
    PRIMARY KEY (article_id, compound_id)
);

-- ------------------------------------------------------------
-- Indices
-- ------------------------------------------------------------
CREATE INDEX idx_bioact_compound   ON bioactivities(compound_id);
CREATE INDEX idx_bioact_target     ON bioactivities(target_id);
CREATE INDEX idx_art_comp_compound ON article_compounds(compound_id);
CREATE INDEX idx_art_comp_article  ON article_compounds(article_id);
CREATE INDEX idx_articles_year     ON articles(pub_year);
CREATE INDEX idx_compounds_name    ON compounds(name);