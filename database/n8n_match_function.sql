-- ============================================================
-- Функция match_documents для n8n Supabase Vector Store
-- ============================================================
-- n8n ожидает функцию с именем match_documents для векторного поиска
-- Эта функция адаптирует нашу схему под требования n8n

CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(1024),
    match_count INT DEFAULT 5,
    filter JSONB DEFAULT '{}'::jsonb
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.id,
        t.content,
        jsonb_build_object(
            'thread_id', t.thread_id,
            'group_name', t.group_name,
            'quality_score', t.quality_score,
            'first_message_date', t.first_message_date,
            'message_count', t.message_count
        ) as metadata,
        1 - (t.content_embedding <=> query_embedding) AS similarity
    FROM telegram_threads_content t
    WHERE 1 - (t.content_embedding <=> query_embedding) > 0.5
    ORDER BY t.content_embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION match_documents IS 'n8n compatible vector search function for telegram_threads_content';

-- ============================================================
-- Тестовый запрос (опционально):
-- SELECT * FROM match_documents(
--     '[0.1, 0.2, ...]'::vector(1024),
--     5
-- );
-- ============================================================
