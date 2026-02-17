-- ============================================================
-- TuExpertoFiscal NAIL - Vector Search Schema with pgvector
-- Векторное хранилище для семантического поиска
-- ============================================================

-- Включаем необходимые расширения
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- ТАБЛИЦЫ ДЛЯ ВЕКТОРНОГО ПОИСКА
-- ============================================================

-- ============================================================
-- 1. telegram_threads_content
-- Полный контент Telegram тредов с векторами
-- ============================================================

CREATE TABLE telegram_threads_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Связь с метаданными
    thread_id BIGINT NOT NULL,
    group_name TEXT NOT NULL,

    -- Контент
    content TEXT NOT NULL,
    first_message TEXT,
    last_message TEXT,

    -- Векторное представление (multilingual-e5-large: 1024 dimensions)
    content_embedding vector(1024),

    -- Метаданные
    message_count INTEGER DEFAULT 0,
    topics TEXT[],
    keywords TEXT[],
    quality_score FLOAT DEFAULT 0.0,

    -- Категории
    tax_related BOOLEAN DEFAULT FALSE,
    visa_related BOOLEAN DEFAULT FALSE,
    business_related BOOLEAN DEFAULT FALSE,

    -- Временные метки
    first_message_date TIMESTAMPTZ,
    last_updated TIMESTAMPTZ,

    -- Дополнительные данные
    metadata JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(thread_id, group_name)
);

-- Индексы для быстрого поиска
CREATE INDEX idx_telegram_content_group ON telegram_threads_content(group_name);
CREATE INDEX idx_telegram_content_date ON telegram_threads_content(last_updated DESC);
CREATE INDEX idx_telegram_content_quality ON telegram_threads_content(quality_score DESC);
CREATE INDEX idx_telegram_content_topics ON telegram_threads_content USING GIN(topics);

-- Векторный индекс для семантического поиска (HNSW - быстрее чем IVFFlat)
CREATE INDEX idx_telegram_content_embedding ON telegram_threads_content
USING hnsw (content_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Полнотекстовый индекс для keyword поиска
CREATE INDEX idx_telegram_content_fts ON telegram_threads_content
USING GIN(to_tsvector('spanish', content));

COMMENT ON TABLE telegram_threads_content IS 'Полный контент Telegram тредов с векторными эмбеддингами для гибридного поиска';
COMMENT ON COLUMN telegram_threads_content.content_embedding IS 'Вектор 1024d от multilingual-e5-large (HuggingFace API)';

-- ============================================================
-- 2. pdf_documents_content
-- Чанки PDF документов с векторами
-- ============================================================

CREATE TABLE pdf_documents_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Идентификация документа
    document_id TEXT NOT NULL,
    document_title TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,

    -- Контент чанка
    content TEXT NOT NULL,

    -- Векторное представление (OpenAI text-embedding-3-small: 1536 dimensions)
    content_embedding vector(1536),

    -- Метаданные документа
    document_type TEXT CHECK (document_type IN ('law', 'regulation', 'guide', 'form')),
    document_number TEXT,
    categories TEXT[],

    -- Позиция в документе
    page_number INTEGER,
    section_title TEXT,

    -- Источник
    source_url TEXT,

    -- Региональность
    region TEXT DEFAULT 'national',
    language TEXT DEFAULT 'es',

    -- Временные данные
    publication_date DATE,

    -- Дополнительные данные
    metadata JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(document_id, chunk_index)
);

-- Индексы
CREATE INDEX idx_pdf_content_document ON pdf_documents_content(document_id);
CREATE INDEX idx_pdf_content_type ON pdf_documents_content(document_type);
CREATE INDEX idx_pdf_content_categories ON pdf_documents_content USING GIN(categories);
CREATE INDEX idx_pdf_content_region ON pdf_documents_content(region);

-- Векторный индекс для семантического поиска
CREATE INDEX idx_pdf_content_embedding ON pdf_documents_content
USING hnsw (content_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Полнотекстовый индекс
CREATE INDEX idx_pdf_content_fts ON pdf_documents_content
USING GIN(to_tsvector('spanish', content));

COMMENT ON TABLE pdf_documents_content IS 'Чанки PDF документов с векторными эмбеддингами';
COMMENT ON COLUMN pdf_documents_content.content_embedding IS 'Вектор 1536d от OpenAI text-embedding-3-small';

-- ============================================================
-- 3. news_articles_content
-- Новостные статьи с векторами
-- ============================================================

CREATE TABLE news_articles_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Идентификация
    article_url TEXT NOT NULL UNIQUE,
    article_title TEXT NOT NULL,

    -- Контент
    content TEXT NOT NULL,
    summary TEXT,

    -- Векторное представление (OpenAI: 1536d)
    content_embedding vector(1536),

    -- Метаданные
    news_source TEXT NOT NULL,
    author TEXT,
    published_at TIMESTAMPTZ NOT NULL,

    -- Категоризация
    categories TEXT[],
    keywords TEXT[],
    tax_related BOOLEAN DEFAULT FALSE,

    -- Релевантность
    relevance_score FLOAT DEFAULT 0.0,

    -- Дополнительные данные
    metadata JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_news_content_source ON news_articles_content(news_source);
CREATE INDEX idx_news_content_published ON news_articles_content(published_at DESC);
CREATE INDEX idx_news_content_categories ON news_articles_content USING GIN(categories);
CREATE INDEX idx_news_content_tax ON news_articles_content(tax_related) WHERE tax_related = true;

-- Векторный индекс
CREATE INDEX idx_news_content_embedding ON news_articles_content
USING hnsw (content_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Полнотекстовый индекс
CREATE INDEX idx_news_content_fts ON news_articles_content
USING GIN(to_tsvector('spanish', content));

COMMENT ON TABLE news_articles_content IS 'Новостные статьи с векторными эмбеддингами';

-- ============================================================
-- 4. calendar_deadlines (без векторов - структурированные данные)
-- ============================================================

CREATE TABLE calendar_deadlines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Временные параметры
    deadline_date DATE NOT NULL,
    year INTEGER NOT NULL,
    quarter TEXT CHECK (quarter IN ('Q1', 'Q2', 'Q3', 'Q4')),
    month INTEGER CHECK (month >= 1 AND month <= 12),

    -- Налоговые характеристики
    tax_type TEXT NOT NULL,
    tax_model TEXT,
    description TEXT NOT NULL,

    -- Применимость
    applies_to TEXT[],
    region TEXT DEFAULT 'national',

    -- Требования
    payment_required BOOLEAN DEFAULT TRUE,
    declaration_required BOOLEAN DEFAULT TRUE,
    penalty_for_late TEXT,

    -- Метаданные
    metadata JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(deadline_date, tax_type, tax_model)
);

-- Индексы
CREATE INDEX idx_deadlines_date ON calendar_deadlines(deadline_date);
CREATE INDEX idx_deadlines_year_quarter ON calendar_deadlines(year, quarter);
CREATE INDEX idx_deadlines_tax_type ON calendar_deadlines(tax_type);
CREATE INDEX idx_deadlines_applies_to ON calendar_deadlines USING GIN(applies_to);
CREATE INDEX idx_deadlines_region ON calendar_deadlines(region);

-- Полнотекстовый индекс для поиска по описанию
CREATE INDEX idx_deadlines_fts ON calendar_deadlines
USING GIN(to_tsvector('spanish', description));

COMMENT ON TABLE calendar_deadlines IS 'Налоговые дедлайны (keyword search only, no vectors needed)';

-- ============================================================
-- ФУНКЦИИ ДЛЯ ГИБРИДНОГО ПОИСКА
-- ============================================================

-- Функция: Гибридный поиск в Telegram (vector + keyword)
CREATE OR REPLACE FUNCTION search_telegram_hybrid(
    query_text TEXT,
    query_embedding vector(1024),
    match_limit INT DEFAULT 10,
    similarity_threshold FLOAT DEFAULT 0.5
)
RETURNS TABLE (
    id UUID,
    thread_id BIGINT,
    group_name TEXT,
    content TEXT,
    similarity FLOAT,
    rank FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH vector_search AS (
        SELECT
            t.id,
            t.thread_id,
            t.group_name,
            t.content,
            1 - (t.content_embedding <=> query_embedding) AS similarity,
            ROW_NUMBER() OVER (ORDER BY t.content_embedding <=> query_embedding) AS rank
        FROM telegram_threads_content t
        WHERE 1 - (t.content_embedding <=> query_embedding) > similarity_threshold
        ORDER BY t.content_embedding <=> query_embedding
        LIMIT match_limit * 2
    ),
    keyword_search AS (
        SELECT
            t.id,
            t.thread_id,
            t.group_name,
            t.content,
            ts_rank(to_tsvector('spanish', t.content), plainto_tsquery('spanish', query_text)) AS rank
        FROM telegram_threads_content t
        WHERE to_tsvector('spanish', t.content) @@ plainto_tsquery('spanish', query_text)
        ORDER BY rank DESC
        LIMIT match_limit * 2
    )
    SELECT
        COALESCE(v.id, k.id) as id,
        COALESCE(v.thread_id, k.thread_id) as thread_id,
        COALESCE(v.group_name, k.group_name) as group_name,
        COALESCE(v.content, k.content) as content,
        COALESCE(v.similarity, 0) as similarity,
        (COALESCE(v.rank, 999) + COALESCE(k.rank, 0)) / 2 as rank
    FROM vector_search v
    FULL OUTER JOIN keyword_search k ON v.id = k.id
    ORDER BY rank DESC
    LIMIT match_limit;
END;
$$;

COMMENT ON FUNCTION search_telegram_hybrid IS 'Гибридный поиск (semantic + keyword) в Telegram тредах';

-- Функция: Гибридный поиск в PDF
CREATE OR REPLACE FUNCTION search_pdf_hybrid(
    query_text TEXT,
    query_embedding vector(1536),
    match_limit INT DEFAULT 10,
    similarity_threshold FLOAT DEFAULT 0.5
)
RETURNS TABLE (
    id UUID,
    document_id TEXT,
    document_title TEXT,
    content TEXT,
    similarity FLOAT,
    rank FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH vector_search AS (
        SELECT
            p.id,
            p.document_id,
            p.document_title,
            p.content,
            1 - (p.content_embedding <=> query_embedding) AS similarity,
            ROW_NUMBER() OVER (ORDER BY p.content_embedding <=> query_embedding) AS rank
        FROM pdf_documents_content p
        WHERE 1 - (p.content_embedding <=> query_embedding) > similarity_threshold
        ORDER BY p.content_embedding <=> query_embedding
        LIMIT match_limit * 2
    ),
    keyword_search AS (
        SELECT
            p.id,
            p.document_id,
            p.document_title,
            p.content,
            ts_rank(to_tsvector('spanish', p.content), plainto_tsquery('spanish', query_text)) AS rank
        FROM pdf_documents_content p
        WHERE to_tsvector('spanish', p.content) @@ plainto_tsquery('spanish', query_text)
        ORDER BY rank DESC
        LIMIT match_limit * 2
    )
    SELECT
        COALESCE(v.id, k.id) as id,
        COALESCE(v.document_id, k.document_id) as document_id,
        COALESCE(v.document_title, k.document_title) as document_title,
        COALESCE(v.content, k.content) as content,
        COALESCE(v.similarity, 0) as similarity,
        (COALESCE(v.rank, 999) + COALESCE(k.rank, 0)) / 2 as rank
    FROM vector_search v
    FULL OUTER JOIN keyword_search k ON v.id = k.id
    ORDER BY rank DESC
    LIMIT match_limit;
END;
$$;

COMMENT ON FUNCTION search_pdf_hybrid IS 'Гибридный поиск (semantic + keyword) в PDF документах';

-- ============================================================
-- ТРИГГЕРЫ ДЛЯ АВТОМАТИЧЕСКОГО ОБНОВЛЕНИЯ updated_at
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_telegram_content_updated_at
    BEFORE UPDATE ON telegram_threads_content
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pdf_content_updated_at
    BEFORE UPDATE ON pdf_documents_content
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_news_content_updated_at
    BEFORE UPDATE ON news_articles_content
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_calendar_deadlines_updated_at
    BEFORE UPDATE ON calendar_deadlines
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- ВСПОМОГАТЕЛЬНЫЕ ПРЕДСТАВЛЕНИЯ
-- ============================================================

-- Представление: Статистика по векторному хранилищу
CREATE OR REPLACE VIEW v_vector_store_stats AS
SELECT
    'telegram' as source_type,
    COUNT(*) as total_items,
    COUNT(content_embedding) as items_with_embeddings,
    AVG(quality_score) as avg_quality_score
FROM telegram_threads_content
UNION ALL
SELECT
    'pdf' as source_type,
    COUNT(*) as total_items,
    COUNT(content_embedding) as items_with_embeddings,
    NULL as avg_quality_score
FROM pdf_documents_content
UNION ALL
SELECT
    'news' as source_type,
    COUNT(*) as total_items,
    COUNT(content_embedding) as items_with_embeddings,
    AVG(relevance_score) as avg_quality_score
FROM news_articles_content;

COMMENT ON VIEW v_vector_store_stats IS 'Статистика по векторному хранилищу';

-- ============================================================
-- GRANTS (опционально, настроить под вашего пользователя)
-- ============================================================

-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO your_app_user;

-- ============================================================
-- Developed by NAIL - Nahornyi AI Lab
-- Migration from Elasticsearch to Supabase + pgvector
-- ============================================================
