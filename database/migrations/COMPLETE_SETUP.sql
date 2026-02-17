-- ============================================================
-- ПОЛНАЯ УСТАНОВКА БД: База знаний + Пользователи
-- Удаляет старые таблицы базы знаний, создает или сохраняет таблицы пользователей
-- ============================================================

-- ============================================================
-- ШАГ 1: Удаляем ВСЕ старые таблицы базы знаний
-- ============================================================

DROP FUNCTION IF EXISTS search_telegram_hybrid CASCADE;
DROP FUNCTION IF EXISTS search_pdf_hybrid CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column CASCADE;

DROP VIEW IF EXISTS v_vector_store_stats CASCADE;
DROP VIEW IF EXISTS v_active_sources_with_logs CASCADE;
DROP VIEW IF EXISTS v_top_telegram_threads CASCADE;
DROP VIEW IF EXISTS v_upcoming_deadlines CASCADE;

DROP TABLE IF EXISTS telegram_threads_content CASCADE;
DROP TABLE IF EXISTS pdf_documents_content CASCADE;
DROP TABLE IF EXISTS news_articles_content CASCADE;
DROP TABLE IF EXISTS calendar_deadlines CASCADE;
DROP TABLE IF EXISTS calendar_events CASCADE;
DROP TABLE IF EXISTS telegram_threads_metadata CASCADE;
DROP TABLE IF EXISTS telegram_threads_metadata_old CASCADE;
DROP TABLE IF EXISTS pdf_documents_metadata CASCADE;
DROP TABLE IF EXISTS pdf_documents_metadata_old CASCADE;
DROP TABLE IF EXISTS news_articles_metadata CASCADE;
DROP TABLE IF EXISTS news_articles_metadata_old CASCADE;
DROP TABLE IF EXISTS aeat_resources_metadata CASCADE;
DROP TABLE IF EXISTS knowledge_sources CASCADE;
DROP TABLE IF EXISTS sync_logs CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS sent_reminders CASCADE;
DROP TABLE IF EXISTS tax_deadlines CASCADE;

-- ============================================================
-- ШАГ 2: Включаем расширения
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- ШАГ 3: Создаем/проверяем таблицы пользователей
-- ============================================================

-- users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id BIGINT UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    phone TEXT,
    subscription_status TEXT NOT NULL DEFAULT 'free',
    subscription_expires_at TIMESTAMPTZ,
    role TEXT NOT NULL DEFAULT 'user',
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);

-- dialogue_sessions table
CREATE TABLE IF NOT EXISTS dialogue_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_dialogue_sessions_user_id ON dialogue_sessions(user_id);

-- messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES dialogue_sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    response_text TEXT,
    sources JSONB,
    is_relevant BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at DESC);

-- user_tax_profile table
CREATE TABLE IF NOT EXISTS user_tax_profile (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    profile_data JSONB,
    updated_at TIMESTAMPTZ
);

-- ============================================================
-- ШАГ 4: Создаем таблицы базы знаний с векторами
-- ============================================================

-- telegram_threads_content
CREATE TABLE telegram_threads_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thread_id BIGINT NOT NULL,
    group_name TEXT NOT NULL,
    content TEXT NOT NULL,
    first_message TEXT,
    last_message TEXT,
    content_embedding vector(1024),
    message_count INTEGER DEFAULT 0,
    topics TEXT[],
    keywords TEXT[],
    quality_score FLOAT DEFAULT 0.0,
    tax_related BOOLEAN DEFAULT FALSE,
    visa_related BOOLEAN DEFAULT FALSE,
    business_related BOOLEAN DEFAULT FALSE,
    first_message_date TIMESTAMPTZ,
    last_updated TIMESTAMPTZ,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(thread_id, group_name)
);

CREATE INDEX idx_telegram_content_group ON telegram_threads_content(group_name);
CREATE INDEX idx_telegram_content_date ON telegram_threads_content(last_updated DESC);
CREATE INDEX idx_telegram_content_quality ON telegram_threads_content(quality_score DESC);
CREATE INDEX idx_telegram_content_topics ON telegram_threads_content USING GIN(topics);
CREATE INDEX idx_telegram_content_embedding ON telegram_threads_content
    USING hnsw (content_embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX idx_telegram_content_fts ON telegram_threads_content
    USING GIN(to_tsvector('spanish', content));

COMMENT ON TABLE telegram_threads_content IS 'Telegram треды с векторами (1024d multilingual-e5-large)';

-- pdf_documents_content
CREATE TABLE pdf_documents_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id TEXT NOT NULL,
    document_title TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_embedding vector(1536),
    document_type TEXT CHECK (document_type IN ('law', 'regulation', 'guide', 'form')),
    document_number TEXT,
    categories TEXT[],
    page_number INTEGER,
    section_title TEXT,
    source_url TEXT,
    region TEXT DEFAULT 'national',
    language TEXT DEFAULT 'es',
    publication_date DATE,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(document_id, chunk_index)
);

CREATE INDEX idx_pdf_content_document ON pdf_documents_content(document_id);
CREATE INDEX idx_pdf_content_type ON pdf_documents_content(document_type);
CREATE INDEX idx_pdf_content_categories ON pdf_documents_content USING GIN(categories);
CREATE INDEX idx_pdf_content_region ON pdf_documents_content(region);
CREATE INDEX idx_pdf_content_embedding ON pdf_documents_content
    USING hnsw (content_embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX idx_pdf_content_fts ON pdf_documents_content
    USING GIN(to_tsvector('spanish', content));

COMMENT ON TABLE pdf_documents_content IS 'PDF чанки с векторами (1536d OpenAI text-embedding-3-small)';

-- news_articles_content
CREATE TABLE news_articles_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    article_url TEXT NOT NULL UNIQUE,
    article_title TEXT NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,
    content_embedding vector(1536),
    news_source TEXT NOT NULL,
    author TEXT,
    published_at TIMESTAMPTZ NOT NULL,
    categories TEXT[],
    keywords TEXT[],
    tax_related BOOLEAN DEFAULT FALSE,
    relevance_score FLOAT DEFAULT 0.0,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_news_content_source ON news_articles_content(news_source);
CREATE INDEX idx_news_content_published ON news_articles_content(published_at DESC);
CREATE INDEX idx_news_content_categories ON news_articles_content USING GIN(categories);
CREATE INDEX idx_news_content_tax ON news_articles_content(tax_related) WHERE tax_related = true;
CREATE INDEX idx_news_content_embedding ON news_articles_content
    USING hnsw (content_embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX idx_news_content_fts ON news_articles_content
    USING GIN(to_tsvector('spanish', content));

COMMENT ON TABLE news_articles_content IS 'Новости с векторами (1536d OpenAI)';

-- calendar_deadlines
CREATE TABLE calendar_deadlines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deadline_date DATE NOT NULL,
    year INTEGER NOT NULL,
    quarter TEXT CHECK (quarter IN ('Q1', 'Q2', 'Q3', 'Q4')),
    month INTEGER CHECK (month >= 1 AND month <= 12),
    tax_type TEXT NOT NULL,
    tax_model TEXT,
    description TEXT NOT NULL,
    applies_to TEXT[],
    region TEXT DEFAULT 'national',
    payment_required BOOLEAN DEFAULT TRUE,
    declaration_required BOOLEAN DEFAULT TRUE,
    penalty_for_late TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(deadline_date, tax_type, tax_model)
);

CREATE INDEX idx_deadlines_date ON calendar_deadlines(deadline_date);
CREATE INDEX idx_deadlines_year_quarter ON calendar_deadlines(year, quarter);
CREATE INDEX idx_deadlines_tax_type ON calendar_deadlines(tax_type);
CREATE INDEX idx_deadlines_applies_to ON calendar_deadlines USING GIN(applies_to);
CREATE INDEX idx_deadlines_region ON calendar_deadlines(region);
CREATE INDEX idx_deadlines_fts ON calendar_deadlines
    USING GIN(to_tsvector('spanish', description));

COMMENT ON TABLE calendar_deadlines IS 'Налоговые дедлайны (только Full-Text Search)';

-- ============================================================
-- ШАГ 5: Функции гибридного поиска
-- ============================================================

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
            t.id, t.thread_id, t.group_name, t.content,
            1 - (t.content_embedding <=> query_embedding) AS similarity,
            ROW_NUMBER() OVER (ORDER BY t.content_embedding <=> query_embedding) AS rank
        FROM telegram_threads_content t
        WHERE 1 - (t.content_embedding <=> query_embedding) > similarity_threshold
        ORDER BY t.content_embedding <=> query_embedding
        LIMIT match_limit * 2
    ),
    keyword_search AS (
        SELECT
            t.id, t.thread_id, t.group_name, t.content,
            ts_rank(to_tsvector('spanish', t.content), plainto_tsquery('spanish', query_text)) AS rank
        FROM telegram_threads_content t
        WHERE to_tsvector('spanish', t.content) @@ plainto_tsquery('spanish', query_text)
        ORDER BY rank DESC
        LIMIT match_limit * 2
    )
    SELECT
        COALESCE(v.id, k.id), COALESCE(v.thread_id, k.thread_id),
        COALESCE(v.group_name, k.group_name), COALESCE(v.content, k.content),
        COALESCE(v.similarity, 0),
        (COALESCE(v.rank, 999) + COALESCE(k.rank, 0)) / 2 as rank
    FROM vector_search v
    FULL OUTER JOIN keyword_search k ON v.id = k.id
    ORDER BY rank DESC
    LIMIT match_limit;
END;
$$;

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
            p.id, p.document_id, p.document_title, p.content,
            1 - (p.content_embedding <=> query_embedding) AS similarity,
            ROW_NUMBER() OVER (ORDER BY p.content_embedding <=> query_embedding) AS rank
        FROM pdf_documents_content p
        WHERE 1 - (p.content_embedding <=> query_embedding) > similarity_threshold
        ORDER BY p.content_embedding <=> query_embedding
        LIMIT match_limit * 2
    ),
    keyword_search AS (
        SELECT
            p.id, p.document_id, p.document_title, p.content,
            ts_rank(to_tsvector('spanish', p.content), plainto_tsquery('spanish', query_text)) AS rank
        FROM pdf_documents_content p
        WHERE to_tsvector('spanish', p.content) @@ plainto_tsquery('spanish', query_text)
        ORDER BY rank DESC
        LIMIT match_limit * 2
    )
    SELECT
        COALESCE(v.id, k.id), COALESCE(v.document_id, k.document_id),
        COALESCE(v.document_title, k.document_title), COALESCE(v.content, k.content),
        COALESCE(v.similarity, 0),
        (COALESCE(v.rank, 999) + COALESCE(k.rank, 0)) / 2 as rank
    FROM vector_search v
    FULL OUTER JOIN keyword_search k ON v.id = k.id
    ORDER BY rank DESC
    LIMIT match_limit;
END;
$$;

-- ============================================================
-- ШАГ 6: Триггеры
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
-- ШАГ 7: Представления
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
-- Проверка: Показать все таблицы
-- ============================================================

SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as columns
FROM information_schema.tables t
WHERE table_schema = 'public'
AND table_type = 'BASE TABLE'
ORDER BY table_name;
