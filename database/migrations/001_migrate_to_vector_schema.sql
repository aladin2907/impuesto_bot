-- ============================================================
-- Миграция: Обновление старой схемы для поддержки pgvector
-- ============================================================

-- Шаг 1: Включаем pgvector расширение
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- Шаг 2: Удаляем старые Elasticsearch-специфичные поля
-- ============================================================

-- Из telegram_threads_metadata (если существует)
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_name = 'telegram_threads_metadata'
    ) THEN
        -- Удаляем Elasticsearch поля
        ALTER TABLE telegram_threads_metadata
            DROP COLUMN IF EXISTS indexed_in_elasticsearch,
            DROP COLUMN IF EXISTS elasticsearch_index_name,
            DROP COLUMN IF EXISTS elasticsearch_doc_id,
            DROP COLUMN IF EXISTS last_indexed_at;

        RAISE NOTICE 'Removed Elasticsearch columns from telegram_threads_metadata';
    END IF;
END $$;

-- Из pdf_documents_metadata (если существует)
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_name = 'pdf_documents_metadata'
    ) THEN
        ALTER TABLE pdf_documents_metadata
            DROP COLUMN IF EXISTS indexed_in_elasticsearch,
            DROP COLUMN IF EXISTS elasticsearch_index_name,
            DROP COLUMN IF EXISTS last_indexed_at;

        RAISE NOTICE 'Removed Elasticsearch columns from pdf_documents_metadata';
    END IF;
END $$;

-- Из news_articles_metadata (если существует)
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_name = 'news_articles_metadata'
    ) THEN
        ALTER TABLE news_articles_metadata
            DROP COLUMN IF EXISTS indexed_in_elasticsearch,
            DROP COLUMN IF EXISTS elasticsearch_index_name,
            DROP COLUMN IF EXISTS elasticsearch_doc_id,
            DROP COLUMN IF EXISTS last_indexed_at;

        RAISE NOTICE 'Removed Elasticsearch columns from news_articles_metadata';
    END IF;
END $$;

-- Из calendar_deadlines (если существует старая версия)
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_name = 'calendar_deadlines'
    ) THEN
        ALTER TABLE calendar_deadlines
            DROP COLUMN IF EXISTS indexed_in_elasticsearch,
            DROP COLUMN IF EXISTS elasticsearch_doc_id;

        RAISE NOTICE 'Removed Elasticsearch columns from calendar_deadlines';
    END IF;
END $$;

-- ============================================================
-- Шаг 3: Переименовываем старые таблицы (если они существуют)
-- ============================================================

-- Переименовываем metadata таблицы, чтобы не конфликтовать с новыми content таблицами
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'telegram_threads_metadata') THEN
        ALTER TABLE telegram_threads_metadata RENAME TO telegram_threads_metadata_old;
        RAISE NOTICE 'Renamed telegram_threads_metadata to telegram_threads_metadata_old';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'pdf_documents_metadata') THEN
        ALTER TABLE pdf_documents_metadata RENAME TO pdf_documents_metadata_old;
        RAISE NOTICE 'Renamed pdf_documents_metadata to pdf_documents_metadata_old';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'news_articles_metadata') THEN
        ALTER TABLE news_articles_metadata RENAME TO news_articles_metadata_old;
        RAISE NOTICE 'Renamed news_articles_metadata to news_articles_metadata_old';
    END IF;
END $$;

-- ============================================================
-- Шаг 4: Создаем новые таблицы
-- ============================================================

-- Запускаем новую схему
\i /path/to/vector_schema.sql

-- Примечание: В Supabase Dashboard нужно будет выполнить содержимое vector_schema.sql

-- ============================================================
-- Шаг 5: Миграция данных (опционально)
-- ============================================================

-- Если нужно перенести данные из старых таблиц в новые:

-- Миграция Telegram тредов
-- INSERT INTO telegram_threads_content (
--     thread_id,
--     group_name,
--     content,
--     first_message,
--     last_message,
--     message_count,
--     topics,
--     keywords,
--     quality_score,
--     tax_related,
--     visa_related,
--     business_related,
--     first_message_date,
--     last_updated,
--     metadata
-- )
-- SELECT
--     thread_id,
--     group_name,
--     COALESCE(raw_data->>'content', ''),
--     raw_data->>'first_message',
--     raw_data->>'last_message',
--     message_count,
--     topics,
--     keywords,
--     quality_score,
--     tax_related,
--     visa_related,
--     business_related,
--     first_message_date,
--     last_updated,
--     raw_data
-- FROM telegram_threads_metadata_old
-- WHERE is_deleted = FALSE;

-- ПРИМЕЧАНИЕ: Векторы (content_embedding) нужно будет сгенерировать отдельно
-- через Python скрипт, используя HuggingFace API

-- ============================================================
-- Шаг 6: Удаляем старые таблицы (ОСТОРОЖНО!)
-- ============================================================

-- Раскомментируйте ТОЛЬКО после успешной миграции данных!

-- DROP TABLE IF EXISTS telegram_threads_metadata_old CASCADE;
-- DROP TABLE IF EXISTS pdf_documents_metadata_old CASCADE;
-- DROP TABLE IF EXISTS news_articles_metadata_old CASCADE;
-- DROP TABLE IF EXISTS aeat_resources_metadata CASCADE;
-- DROP TABLE IF EXISTS knowledge_sources CASCADE;
-- DROP TABLE IF EXISTS sync_logs CASCADE;

-- ============================================================
-- ГОТОВО!
-- ============================================================

-- Проверка структуры
SELECT
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name IN (
    'telegram_threads_content',
    'pdf_documents_content',
    'news_articles_content',
    'calendar_deadlines'
)
ORDER BY table_name, ordinal_position;
