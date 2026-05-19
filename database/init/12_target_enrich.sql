-- ============================================================
-- Migration: enriquecimento de targets
-- Fonte: endpoint /target/{id} do ChEMBL (mesma requisição já feita
-- por fetch_target — sem chamada extra)
--
-- Adiciona:
--   - targets.tax_id, species_group_flag
--   - target_components (subunidades proteicas)
--      • accession (UniProt: P00519)
--      • gene_symbol (ABL1)
--      • component_type / description / relationship
--   - target_xrefs (cross-references por componente)
--      • PDB structures (estrutura 3D)
--      • GO annotations (function/process/component)
--      • UniProt / Reactome / InterPro / Pfam / HGNC / PharmGKB
--
-- Idempotente: re-execução sobre banco já migrado é no-op.
-- ============================================================

-- ------------------------------------------------------------
-- targets — colunas adicionais
-- ------------------------------------------------------------
ALTER TABLE targets ADD COLUMN IF NOT EXISTS tax_id              INTEGER;
ALTER TABLE targets ADD COLUMN IF NOT EXISTS species_group_flag  BOOLEAN;

CREATE INDEX IF NOT EXISTS idx_targets_tax_id ON targets(tax_id);


-- ------------------------------------------------------------
-- target_components — subunidades do alvo
-- ------------------------------------------------------------
-- Exemplo (ABL1 = SINGLE PROTEIN, 1 componente):
--   component_id = 173, accession = P00519, gene_symbol = ABL1,
--   component_type = PROTEIN
--
-- Para PROTEIN COMPLEX, há múltiplos componentes (ex: receptores GABA).
CREATE TABLE IF NOT EXISTS target_components (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    target_id             UUID NOT NULL REFERENCES targets(id) ON DELETE CASCADE,
    component_id          INTEGER NOT NULL,    -- PK do ChEMBL
    accession             TEXT,                -- UniProt: P00519
    gene_symbol           TEXT,                -- ABL1
    component_type        TEXT,                -- PROTEIN | RNA | DNA | …
    component_description TEXT,                -- "Tyrosine-protein kinase ABL1"
    relationship          TEXT,                -- SINGLE PROTEIN | EQUIVALENT TO | …
    created_at            TIMESTAMP DEFAULT NOW(),
    UNIQUE (target_id, component_id)
);

CREATE INDEX IF NOT EXISTS idx_tc_target_id    ON target_components(target_id);
CREATE INDEX IF NOT EXISTS idx_tc_accession    ON target_components(accession);
CREATE INDEX IF NOT EXISTS idx_tc_gene_symbol  ON target_components(gene_symbol);


-- ------------------------------------------------------------
-- target_xrefs — cross-references por componente
-- ------------------------------------------------------------
-- Cada componente proteico tem dezenas de xrefs:
--   PDB (3D), GO (function/process/component), UniProt, Reactome
--   pathways, InterPro/Pfam domains, HGNC, PharmGKB...
--
-- Estrutura genérica (src_db + id) cobre todos os providers sem
-- precisar de uma tabela por fonte.
CREATE TABLE IF NOT EXISTS target_xrefs (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    component_id  UUID NOT NULL REFERENCES target_components(id) ON DELETE CASCADE,
    xref_src_db   TEXT NOT NULL,    -- PDB | PDBe | GoFunction | GoProcess | UniProt | …
    xref_id       TEXT NOT NULL,    -- valor identificador (3UYO, P00519, GO:0005524…)
    xref_name     TEXT,             -- descrição human-readable (quando houver)
    created_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE (component_id, xref_src_db, xref_id)
);

CREATE INDEX IF NOT EXISTS idx_tx_component_id ON target_xrefs(component_id);
CREATE INDEX IF NOT EXISTS idx_tx_src_db       ON target_xrefs(xref_src_db);
CREATE INDEX IF NOT EXISTS idx_tx_id           ON target_xrefs(xref_id);


-- ============================================================
-- Views
-- ============================================================

-- Genes/UniProt por target (1 linha por componente, simples de consumir)
CREATE OR REPLACE VIEW v_target_genes AS
SELECT
    t.chembl_id      AS target_chembl_id,
    t.name           AS target_name,
    t.organism,
    t.tax_id,
    tc.gene_symbol,
    tc.accession     AS uniprot_accession,
    tc.component_type,
    tc.component_description
FROM targets            t
JOIN target_components  tc ON tc.target_id = t.id
ORDER BY t.chembl_id, tc.gene_symbol;


-- Estruturas PDB resolvidas por target (útil pra viewer 3D)
CREATE OR REPLACE VIEW v_target_pdbs AS
SELECT
    t.chembl_id    AS target_chembl_id,
    t.name         AS target_name,
    tc.gene_symbol,
    tx.xref_id     AS pdb_id
FROM targets             t
JOIN target_components   tc ON tc.target_id    = t.id
JOIN target_xrefs        tx ON tx.component_id = tc.id
WHERE tx.xref_src_db IN ('PDB', 'PDBe')
ORDER BY t.chembl_id, tx.xref_id;


-- Funções/processos GO por target
CREATE OR REPLACE VIEW v_target_go AS
SELECT
    t.chembl_id      AS target_chembl_id,
    tc.gene_symbol,
    tx.xref_src_db   AS go_category,   -- GoFunction | GoProcess | GoComponent
    tx.xref_id       AS go_id,
    tx.xref_name     AS go_term
FROM targets             t
JOIN target_components   tc ON tc.target_id    = t.id
JOIN target_xrefs        tx ON tx.component_id = tc.id
WHERE tx.xref_src_db LIKE 'Go%'
ORDER BY t.chembl_id, tx.xref_src_db, tx.xref_id;
