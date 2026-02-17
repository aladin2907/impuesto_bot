-- ============================================================
-- Безопасная миграция: Добавление векторных таблиц
-- Не трогает существующие таблицы
-- ============================================================

-- Шаг 1: Включаем pgvector расширение
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- Создаем ТОЛЬКО новые таблицы с векторами
-- ============================================================

-- 1. telegram_threads_content (НОВАЯ)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_name = 'telegram_threads_content'
    ) THEN
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

        -- Индексы
        CREATE INDEX idx_telegram_content_group ON telegram_threads_content(group_name);
        CREATE INDEX idx_telegram_content_date ON telegram_threads_content(last_updated DESC);
        CREATE INDEX idx_telegram_content_quality ON telegram_threads_content(quality_score DESC);
        CREATE INDEX idx_telegram_content_topics ON telegram_threads_content USING GIN(topics);

        -- Векторный индекс
        CREATE INDEX idx_telegram_content_embedding ON telegram_threads_content
        USING hnsw (content_embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);

        -- Полнотекстовый индекс
        CREATE INDEX idx_telegram_content_fts ON telegram_threads_content
        USING GIN(to_tsvector('spanish', content));

        COMMENT ON TABLE telegram_threads_content IS 'Полный контент Telegram тредов с векторными эмбеддингами';

        RAISE NOTICE 'Created telegram_threads_content table';
    ELSE
        RAISE NOTICE 'Table telegram_threads_content already exists, skipping';
    END IF;
END $$;

-- 2. pdf_documents_content (НОВАЯ)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_name = 'pdf_documents_content'
    ) THEN
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

        -- Векторный индекс
        CREATE INDEX idx_pdf_content_embedding ON pdf_documents_content
        USING hnsw (content_embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);

        -- Полнотекстовый индекс
        CREATE INDEX idx_pdf_content_fts ON pdf_documents_content
        USING GIN(to_tsvector('spanish', content));

        COMMENT ON TABLE pdf_documents_content IS 'Чанки PDF документов с векторными эмбеддингами';

        RAISE NOTICE 'Created pdf_documents_content table';
    ELSE
        RAISE NOTICE 'Table pdf_documents_content already exists, skipping';
    END IF;
END $$;

-- 3. news_articles_content (НОВАЯ)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_name = 'news_articles_content'
    ) THEN
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

        RAISE NOTICE 'Created news_articles_content table';
    ELSE
        RAISE NOTICE 'Table news_articles_content already exists, skipping';
    END IF;
END $$;

-- 4. Обновляем calendar_deadlines (удаляем Elasticsearch поля, если есть)
DO $$
BEGIN
    -- Удаляем Elasticsearch поля из существующей таблицы
    ALTER TABLE calendar_deadlines DROP COLUMN IF EXISTS indexed_in_elasticsearch;
    ALTER TABLE calendar_deadlines DROP COLUMN IF EXISTS elasticsearch_doc_id;
    ALTER TABLE calendar_deadlines DROP COLUMN IF EXISTS reminder_sent_count;
    ALTER TABLE calendar_deadlines DROP COLUMN IF EXISTS last_reminder_sent_at;

    RAISE NOTICE 'Cleaned up calendar_deadlines from Elasticsearch columns';

    -- Добавляем Full-Text Search индекс, если его нет
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'calendar_deadlines'
        AND indexname = 'idx_deadlines_fts'
    ) THEN
        CREATE INDEX idx_deadlines_fts ON calendar_deadlines
        USING GIN(to_tsvector('spanish', description));

        RAISE NOTICE 'Added Full-Text Search index to calendar_deadlines';
    END IF;
END $$;

-- ============================================================
-- ФУНКЦИИ ДЛЯ ГИБРИДНОГО ПОИСКА
-- ============================================================

-- Функция: Гибридный поиск в Telegram
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

-- ============================================================
-- ТРИГГЕРЫ
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Создаем триггеры только если таблицы новые
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_telegram_content_updated_at') THEN
        CREATE TRIGGER update_telegram_content_updated_at
            BEFORE UPDATE ON telegram_threads_content
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_pdf_content_updated_at') THEN
        CREATE TRIGGER update_pdf_content_updated_at
            BEFORE UPDATE ON pdf_documents_content
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_news_content_updated_at') THEN
        CREATE TRIGGER update_news_content_updated_at
            BEFORE UPDATE ON news_articles_content
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- ============================================================
-- ПРЕДСТАВЛЕНИЕ
-- ============================================================

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

-- ============================================================
-- Проверка результатов
-- ============================================================

-- Показать все созданные таблицы
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
AND table_name IN (
    'telegram_threads_content',
    'pdf_documents_content',
    'news_articles_content',
    'calendar_deadlines'
)
ORDER BY table_name;

-- Показать статистику
SELECT * FROM v_vector_store_stats;
