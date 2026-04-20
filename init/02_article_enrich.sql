-- ============================================================
-- Migration: enriquecimento de artigos
-- Adiciona campos extraídos via efetch XML do PubMed
-- ============================================================

ALTER TABLE articles
    ADD COLUMN IF NOT EXISTS mesh_terms JSONB,  -- termos MeSH indexados
    ADD COLUMN IF NOT EXISTS keywords   JSONB,  -- palavras-chave dos autores
    ADD COLUMN IF NOT EXISTS pub_types  JSONB;  -- tipos: Review, Clinical Trial…

-- Índice GIN para buscas dentro dos arrays JSON
CREATE INDEX IF NOT EXISTS idx_articles_mesh
    ON articles USING GIN (mesh_terms);

CREATE INDEX IF NOT EXISTS idx_articles_keywords
    ON articles USING GIN (keywords);

COMMENT ON COLUMN articles.mesh_terms IS
    'Array de objetos {term: text, major: bool} vindos do MeshHeadingList do PubMed';

COMMENT ON COLUMN articles.keywords IS
    'Array de strings vindas do KeywordList do PubMed (palavras-chave dos autores)';

COMMENT ON COLUMN articles.pub_types IS
    'Array de strings: Journal Article, Review, Clinical Trial, etc.';