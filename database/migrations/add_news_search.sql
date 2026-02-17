-- ============================================================
-- Функция: Гибридный поиск в News (vector + keyword)
-- Создана для агента налогового консультанта
-- ============================================================

CREATE OR REPLACE FUNCTION search_news_hybrid(
    query_text TEXT,
    query_embedding vector(1536),
    match_limit INT DEFAULT 10,
    similarity_threshold FLOAT DEFAULT 0.5,
    filter_date_from TIMESTAMPTZ DEFAULT NULL,
    filter_date_to TIMESTAMPTZ DEFAULT NULL,
    filter_news_source TEXT DEFAULT NULL,
    filter_categories TEXT[] DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    article_url TEXT,
    article_title TEXT,
    content TEXT,
    published_at TIMESTAMPTZ,
    news_source TEXT,
    categories TEXT[],
    similarity FLOAT,
    rank FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH vector_search AS (
        SELECT
            n.id,
            n.article_url,
            n.article_title,
            n.content,
            n.published_at,
            n.news_source,
            n.categories,
            1 - (n.content_embedding <=> query_embedding) AS similarity,
            ROW_NUMBER() OVER (ORDER BY n.content_embedding <=> query_embedding) AS rank
        FROM news_articles_content n
        WHERE 1 - (n.content_embedding <=> query_embedding) > similarity_threshold
            AND (filter_date_from IS NULL OR n.published_at >= filter_date_from)
            AND (filter_date_to IS NULL OR n.published_at <= filter_date_to)
            AND (filter_news_source IS NULL OR n.news_source = filter_news_source)
            AND (filter_categories IS NULL OR n.categories && filter_categories)
        ORDER BY n.content_embedding <=> query_embedding
        LIMIT match_limit * 2
    ),
    keyword_search AS (
        SELECT
            n.id,
            n.article_url,
            n.article_title,
            n.content,
            n.published_at,
            n.news_source,
            n.categories,
            ts_rank(to_tsvector('spanish', n.content), plainto_tsquery('spanish', query_text)) AS rank
        FROM news_articles_content n
        WHERE to_tsvector('spanish', n.content) @@ plainto_tsquery('spanish', query_text)
            AND (filter_date_from IS NULL OR n.published_at >= filter_date_from)
            AND (filter_date_to IS NULL OR n.published_at <= filter_date_to)
            AND (filter_news_source IS NULL OR n.news_source = filter_news_source)
            AND (filter_categories IS NULL OR n.categories && filter_categories)
        ORDER BY rank DESC
        LIMIT match_limit * 2
    )
    SELECT
        COALESCE(v.id, k.id) as id,
        COALESCE(v.article_url, k.article_url) as article_url,
        COALESCE(v.article_title, k.article_title) as article_title,
        COALESCE(v.content, k.content) as content,
        COALESCE(v.published_at, k.published_at) as published_at,
        COALESCE(v.news_source, k.news_source) as news_source,
        COALESCE(v.categories, k.categories) as categories,
        COALESCE(v.similarity, 0) as similarity,
        (COALESCE(v.rank, 999) + COALESCE(k.rank, 0)) / 2 as rank
    FROM vector_search v
    FULL OUTER JOIN keyword_search k ON v.id = k.id
    ORDER BY rank DESC
    LIMIT match_limit;
END;
$$;

COMMENT ON FUNCTION search_news_hybrid IS 'Гибридный поиск (semantic + keyword) в новостях с фильтрацией по дате и источнику';

-- ============================================================
-- Тест функции (опционально):
-- SELECT * FROM search_news_hybrid(
--     'cambios en impuestos 2025',
--     '[0.1, 0.2, ...]'::vector(1536),
--     5,
--     0.5
-- );
-- ============================================================
