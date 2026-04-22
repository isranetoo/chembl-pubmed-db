-- ============================================================
-- Migration: full-text search (FTS)
-- Adiciona tsvector em articles, compounds e targets.
-- Triggers mantêm os vetores atualizados automaticamente.
-- Função search_all() faz busca unificada nas três tabelas.
-- ============================================================


-- ============================================================
-- 1. ARTIGOS
-- Pondera: título > abstract > journal
-- ============================================================

ALTER TABLE articles
    ADD COLUMN IF NOT EXISTS fts tsvector;

-- Popular para linhas existentes
UPDATE articles
SET fts =
    setweight(to_tsvector('english', COALESCE(title,    '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(abstract, '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(journal,  '')), 'C');

-- Índice GIN para buscas rápidas
CREATE INDEX IF NOT EXISTS idx_articles_fts ON articles USING GIN (fts);

-- Trigger: atualiza fts ao inserir ou alterar
CREATE OR REPLACE FUNCTION trg_articles_fts()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.fts :=
        setweight(to_tsvector('english', COALESCE(NEW.title,    '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.abstract, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.journal,  '')), 'C');
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trig_articles_fts ON articles;
CREATE TRIGGER trig_articles_fts
    BEFORE INSERT OR UPDATE OF title, abstract, journal
    ON articles
    FOR EACH ROW EXECUTE FUNCTION trg_articles_fts();


-- ============================================================
-- 2. COMPOSTOS
-- Pondera: nome > chembl_id > formula
-- ============================================================

ALTER TABLE compounds
    ADD COLUMN IF NOT EXISTS fts tsvector;

UPDATE compounds
SET fts =
    setweight(to_tsvector('english', COALESCE(name,             '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(chembl_id,        '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(molecular_formula,'')), 'C');

CREATE INDEX IF NOT EXISTS idx_compounds_fts ON compounds USING GIN (fts);

CREATE OR REPLACE FUNCTION trg_compounds_fts()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.fts :=
        setweight(to_tsvector('english', COALESCE(NEW.name,             '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.chembl_id,        '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.molecular_formula,'')), 'C');
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trig_compounds_fts ON compounds;
CREATE TRIGGER trig_compounds_fts
    BEFORE INSERT OR UPDATE OF name, chembl_id, molecular_formula
    ON compounds
    FOR EACH ROW EXECUTE FUNCTION trg_compounds_fts();


-- ============================================================
-- 3. ALVOS (targets)
-- Pondera: nome > organismo > tipo
-- ============================================================

ALTER TABLE targets
    ADD COLUMN IF NOT EXISTS fts tsvector;

UPDATE targets
SET fts =
    setweight(to_tsvector('english', COALESCE(name,     '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(organism, '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(type,     '')), 'C');

CREATE INDEX IF NOT EXISTS idx_targets_fts ON targets USING GIN (fts);

CREATE OR REPLACE FUNCTION trg_targets_fts()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.fts :=
        setweight(to_tsvector('english', COALESCE(NEW.name,     '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.organism, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.type,     '')), 'C');
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trig_targets_fts ON targets;
CREATE TRIGGER trig_targets_fts
    BEFORE INSERT OR UPDATE OF name, organism, type
    ON targets
    FOR EACH ROW EXECUTE FUNCTION trg_targets_fts();


-- ============================================================
-- 4. FUNÇÃO DE BUSCA UNIFICADA
--
-- Uso:
--   SELECT * FROM search_all('aspirin inflammation');
--   SELECT * FROM search_all('cyclooxygenase inhibitor');
--   SELECT * FROM search_all('diabetes metformin');
--
-- Retorna resultados de articles, compounds e targets numa
-- única query, ordenados por relevância (ts_rank_cd).
--
-- Parâmetros:
--   query_text  — texto livre, palavras separadas por espaço
--   max_results — máximo por tabela (default 10)
-- ============================================================

CREATE OR REPLACE FUNCTION search_all(
    query_text  TEXT,
    max_results INTEGER DEFAULT 10
)
RETURNS TABLE (
    source      TEXT,    -- 'article' | 'compound' | 'target'
    id          UUID,
    label       TEXT,    -- título / nome
    detail      TEXT,    -- abstract snippet / chembl_id / organismo
    rank        REAL,    -- relevância (maior = mais relevante)
    highlight   TEXT     -- trecho com os termos marcados
)
LANGUAGE plpgsql AS $$
DECLARE
    tsq tsquery;
BEGIN
    -- Converte texto livre em tsquery:
    -- "aspirin inflammation" → 'aspirin' & 'inflammation'
    -- Usa plainto_tsquery para tratar espaços como AND automaticamente
    tsq := plainto_tsquery('english', query_text);

    RETURN QUERY

    SELECT * FROM (
        -- Artigos
        SELECT
            'article'::TEXT,
            a.id,
            COALESCE(a.title, '(sem título)'),
            LEFT(COALESCE(a.abstract, ''), 200),
            ts_rank_cd(a.fts, tsq),
            ts_headline(
                'english', COALESCE(a.title, '') || ' ' || COALESCE(a.abstract, ''),
                tsq,
                'MaxWords=20, MinWords=5, MaxFragments=2, FragmentDelimiter=" … "'
            )
        FROM articles a
        WHERE a.fts @@ tsq
        ORDER BY ts_rank_cd(a.fts, tsq) DESC
        LIMIT max_results
    ) _art

    UNION ALL

    SELECT * FROM (
        -- Compostos
        SELECT
            'compound'::TEXT,
            c.id,
            c.name,
            c.chembl_id || COALESCE(' — ' || c.molecular_formula, ''),
            ts_rank_cd(c.fts, tsq),
            ts_headline(
                'english', c.name || ' ' || COALESCE(c.chembl_id, ''),
                tsq,
                'MaxWords=10, MinWords=3'
            )
        FROM compounds c
        WHERE c.fts @@ tsq
        ORDER BY ts_rank_cd(c.fts, tsq) DESC
        LIMIT max_results
    ) _cmp

    UNION ALL

    SELECT * FROM (
        -- Alvos
        SELECT
            'target'::TEXT,
            t.id,
            t.name,
            COALESCE(t.organism, '') || COALESCE(' — ' || t.type, ''),
            ts_rank_cd(t.fts, tsq),
            ts_headline(
                'english', t.name || ' ' || COALESCE(t.organism, ''),
                tsq,
                'MaxWords=10, MinWords=3'
            )
        FROM targets t
        WHERE t.fts @@ tsq
        ORDER BY ts_rank_cd(t.fts, tsq) DESC
        LIMIT max_results
    ) _tgt

    ORDER BY rank DESC;

END;
$$;


-- ============================================================
-- 5. VIEWS AUXILIARES
-- ============================================================

-- Busca só em artigos com snippet de abstract
CREATE OR REPLACE VIEW v_fts_articles AS
SELECT
    a.pmid,
    a.title,
    a.journal,
    a.pub_year,
    LEFT(a.abstract, 300)   AS abstract_preview,
    a.fts
FROM articles a
WHERE a.fts IS NOT NULL;

-- Busca só em compostos
CREATE OR REPLACE VIEW v_fts_compounds AS
SELECT
    c.chembl_id,
    c.name,
    c.molecular_formula,
    c.mol_weight,
    c.fts
FROM compounds c
WHERE c.fts IS NOT NULL;


-- ============================================================
-- Exemplos de uso
-- ============================================================
-- Busca unificada (articles + compounds + targets):
--   SELECT * FROM search_all('aspirin pain');
--
-- Busca apenas em artigos com rank explícito:
--   SELECT title, pub_year, ts_rank_cd(fts, q) AS rank
--   FROM articles, plainto_tsquery('english','aspirin inflammation') q
--   WHERE fts @@ q
--   ORDER BY rank DESC;
--
-- Busca com prefixo (autocomplete):
--   SELECT name FROM compounds
--   WHERE fts @@ to_tsquery('english', 'aspir:*');
--
-- Busca por frase exata:
--   SELECT title FROM articles
--   WHERE fts @@ phraseto_tsquery('english', 'cardiovascular disease');