-- ============================================================
-- TuExpertoFiscal NAIL - Knowledge Base Schema
-- База знаний для хранения метаданных всех источников
-- ============================================================

-- Включаем расширение для UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- 1. Таблица: knowledge_sources
-- Реестр всех источников знаний
-- ============================================================

CREATE TABLE knowledge_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type TEXT NOT NULL CHECK (source_type IN ('telegram', 'pdf', 'calendar', 'news', 'aeat', 'regional')),
    source_name TEXT NOT NULL,
    source_url TEXT,
    description TEXT,
    language TEXT DEFAULT 'es',
    is_active BOOLEAN DEFAULT TRUE,
    last_synced_at TIMESTAMPTZ,
    next_sync_at TIMESTAMPTZ,
    sync_frequency TEXT CHECK (sync_frequency IN ('daily', 'weekly', 'monthly', 'manual')),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sources_type ON knowledge_sources(source_type);
CREATE INDEX idx_sources_active ON knowledge_sources(is_active);
CREATE INDEX idx_sources_next_sync ON knowledge_sources(next_sync_at);

COMMENT ON TABLE knowledge_sources IS 'Реестр всех источников знаний';
COMMENT ON COLUMN knowledge_sources.source_type IS 'Тип источника: telegram, pdf, calendar, news, aeat, regional';
COMMENT ON COLUMN knowledge_sources.sync_frequency IS 'Частота синхронизации: daily, weekly, monthly, manual';

-- ============================================================
-- 2. Таблица: telegram_threads_metadata
-- Метаданные Telegram тредов
-- ============================================================

CREATE TABLE telegram_threads_metadata (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES knowledge_sources(id) ON DELETE CASCADE,
    
    -- Идентификаторы
    thread_id BIGINT NOT NULL,
    group_name TEXT NOT NULL,
    group_username TEXT,
    
    -- Временные метки
    first_message_date TIMESTAMPTZ NOT NULL,
    last_updated TIMESTAMPTZ NOT NULL,
    
    -- Характеристики
    message_count INTEGER NOT NULL,
    max_depth INTEGER DEFAULT 0,
    
    -- Тематика
    topics TEXT[],
    keywords TEXT[],
    tax_related BOOLEAN DEFAULT FALSE,
    visa_related BOOLEAN DEFAULT FALSE,
    business_related BOOLEAN DEFAULT FALSE,
    
    -- Качество
    quality_score FLOAT DEFAULT 0.0,
    has_questions BOOLEAN DEFAULT FALSE,
    has_answers BOOLEAN DEFAULT FALSE,
    
    -- Индексация
    indexed_in_elasticsearch BOOLEAN DEFAULT FALSE,
    elasticsearch_index_name TEXT,
    elasticsearch_doc_id TEXT,
    last_indexed_at TIMESTAMPTZ,
    
    -- Версионирование
    version INTEGER DEFAULT 1,
    is_deleted BOOLEAN DEFAULT FALSE,
    
    -- Метаданные
    raw_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(thread_id, group_name)
);

CREATE INDEX idx_telegram_threads_source ON telegram_threads_metadata(source_id);
CREATE INDEX idx_telegram_threads_date ON telegram_threads_metadata(last_updated);
CREATE INDEX idx_telegram_threads_topics ON telegram_threads_metadata USING GIN(topics);
CREATE INDEX idx_telegram_threads_quality ON telegram_threads_metadata(quality_score);
CREATE INDEX idx_telegram_threads_elasticsearch ON telegram_threads_metadata(elasticsearch_doc_id);
CREATE INDEX idx_telegram_threads_group ON telegram_threads_metadata(group_name);

COMMENT ON TABLE telegram_threads_metadata IS 'Метаданные Telegram тредов';
COMMENT ON COLUMN telegram_threads_metadata.quality_score IS 'Качество треда от 0.0 до 5.0';
COMMENT ON COLUMN telegram_threads_metadata.raw_data IS 'Полный JSON треда из парсера';

-- ============================================================
-- 3. Таблица: pdf_documents_metadata
-- Метаданные PDF документов (законы, регламенты)
-- ============================================================

CREATE TABLE pdf_documents_metadata (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES knowledge_sources(id) ON DELETE CASCADE,
    
    -- Идентификаторы
    document_title TEXT NOT NULL,
    document_type TEXT NOT NULL CHECK (document_type IN ('law', 'regulation', 'guide', 'form')),
    document_number TEXT,
    
    -- Источник
    source_url TEXT NOT NULL,
    file_path TEXT,
    file_size_bytes BIGINT,
    file_hash TEXT,
    
    -- Версионирование
    publication_date DATE,
    version_date DATE,
    version_number TEXT,
    is_latest_version BOOLEAN DEFAULT TRUE,
    superseded_by UUID REFERENCES pdf_documents_metadata(id),
    
    -- Характеристики
    page_count INTEGER,
    language TEXT DEFAULT 'es',
    region TEXT,
    
    -- Тематика
    categories TEXT[],
    tags TEXT[],
    
    -- Обработка
    chunks_count INTEGER DEFAULT 0,
    processed_at TIMESTAMPTZ,
    processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'error')),
    processing_error TEXT,
    
    -- Индексация
    indexed_in_elasticsearch BOOLEAN DEFAULT FALSE,
    elasticsearch_index_name TEXT,
    last_indexed_at TIMESTAMPTZ,
    
    -- Метаданные
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pdf_documents_source ON pdf_documents_metadata(source_id);
CREATE INDEX idx_pdf_documents_type ON pdf_documents_metadata(document_type);
CREATE INDEX idx_pdf_documents_categories ON pdf_documents_metadata USING GIN(categories);
CREATE INDEX idx_pdf_documents_version ON pdf_documents_metadata(is_latest_version);
CREATE INDEX idx_pdf_documents_status ON pdf_documents_metadata(processing_status);
CREATE INDEX idx_pdf_documents_region ON pdf_documents_metadata(region);

COMMENT ON TABLE pdf_documents_metadata IS 'Метаданные PDF документов (законы, регламенты)';
COMMENT ON COLUMN pdf_documents_metadata.file_hash IS 'Хеш файла для проверки изменений';
COMMENT ON COLUMN pdf_documents_metadata.superseded_by IS 'Ссылка на новую версию документа';

-- ============================================================
-- 4. Таблица: news_articles_metadata
-- Метаданные новостных статей
-- ============================================================

CREATE TABLE news_articles_metadata (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES knowledge_sources(id) ON DELETE CASCADE,
    
    -- Идентификаторы
    article_url TEXT NOT NULL UNIQUE,
    article_title TEXT NOT NULL,
    
    -- Источник
    news_source TEXT NOT NULL,
    author TEXT,
    
    -- Временные метки
    published_at TIMESTAMPTZ NOT NULL,
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Контент
    summary TEXT,
    content_length INTEGER,
    
    -- Тематика
    categories TEXT[],
    keywords TEXT[],
    tax_related BOOLEAN DEFAULT FALSE,
    
    -- Релевантность
    relevance_score FLOAT DEFAULT 0.0,
    is_relevant BOOLEAN DEFAULT TRUE,
    
    -- Индексация
    indexed_in_elasticsearch BOOLEAN DEFAULT FALSE,
    elasticsearch_index_name TEXT,
    elasticsearch_doc_id TEXT,
    last_indexed_at TIMESTAMPTZ,
    
    -- Метаданные
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_news_source ON news_articles_metadata(source_id);
CREATE INDEX idx_news_published ON news_articles_metadata(published_at);
CREATE INDEX idx_news_categories ON news_articles_metadata USING GIN(categories);
CREATE INDEX idx_news_relevance ON news_articles_metadata(relevance_score);
CREATE INDEX idx_news_tax_related ON news_articles_metadata(tax_related);

COMMENT ON TABLE news_articles_metadata IS 'Метаданные новостных статей';
COMMENT ON COLUMN news_articles_metadata.relevance_score IS 'Релевантность статьи от 0.0 до 1.0';

-- ============================================================
-- 5. Таблица: calendar_deadlines
-- Структурированные налоговые дедлайны
-- ============================================================

CREATE TABLE calendar_deadlines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES knowledge_sources(id) ON DELETE CASCADE,
    
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
    
    -- Дополнительная информация
    payment_required BOOLEAN DEFAULT TRUE,
    declaration_required BOOLEAN DEFAULT TRUE,
    penalty_for_late TEXT,
    
    -- Уведомления
    reminder_sent_count INTEGER DEFAULT 0,
    last_reminder_sent_at TIMESTAMPTZ,
    
    -- Индексация
    indexed_in_elasticsearch BOOLEAN DEFAULT FALSE,
    elasticsearch_doc_id TEXT,
    
    -- Метаданные
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

COMMENT ON TABLE calendar_deadlines IS 'Структурированные налоговые дедлайны';
COMMENT ON COLUMN calendar_deadlines.applies_to IS 'Кому применяется: autonomos, empresas, pymes, etc.';

-- ============================================================
-- 5b. Таблица: calendar_events (сырые события iCalendar)
-- ============================================================

CREATE TABLE calendar_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    uid TEXT NOT NULL,
    calendar_type TEXT NOT NULL,
    summary TEXT,
    dtstart TIMESTAMPTZ,
    dtend TIMESTAMPTZ,
    status TEXT,
    sequence INTEGER,
    last_modified TIMESTAMPTZ,
    description TEXT,
    location TEXT,
    organizer TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    raw TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(uid, calendar_type)
);

CREATE INDEX idx_calendar_events_type ON calendar_events(calendar_type);
CREATE INDEX idx_calendar_events_dtstart ON calendar_events(dtstart);
CREATE INDEX idx_calendar_events_status ON calendar_events(status);

COMMENT ON TABLE calendar_events IS 'Сырые события AEAT iCalendar (Google Calendar)';
COMMENT ON COLUMN calendar_events.calendar_type IS 'Slug источника: renta, iva, declaraciones_informativas и т.д.';

-- ============================================================
-- 6. Таблица: aeat_resources_metadata
-- Метаданные ресурсов AEAT (формы, инструкции)
-- ============================================================

CREATE TABLE aeat_resources_metadata (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES knowledge_sources(id) ON DELETE CASCADE,
    
    -- Идентификаторы
    resource_url TEXT NOT NULL UNIQUE,
    resource_title TEXT NOT NULL,
    resource_type TEXT NOT NULL CHECK (resource_type IN ('form', 'guide', 'instruction', 'faq')),
    
    -- Характеристики
    model_number TEXT,
    fiscal_year INTEGER,
    language TEXT DEFAULT 'es',
    
    -- Версионирование
    version_date DATE,
    is_current_version BOOLEAN DEFAULT TRUE,
    
    -- Файлы
    file_path TEXT,
    file_format TEXT CHECK (file_format IN ('pdf', 'html', 'xml', 'doc', 'xls')),
    file_size_bytes BIGINT,
    
    -- Обработка
    processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'error')),
    processed_at TIMESTAMPTZ,
    
    -- Индексация
    indexed_in_elasticsearch BOOLEAN DEFAULT FALSE,
    elasticsearch_index_name TEXT,
    last_indexed_at TIMESTAMPTZ,
    
    -- Метаданные
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_aeat_resources_type ON aeat_resources_metadata(resource_type);
CREATE INDEX idx_aeat_resources_model ON aeat_resources_metadata(model_number);
CREATE INDEX idx_aeat_resources_version ON aeat_resources_metadata(is_current_version);
CREATE INDEX idx_aeat_resources_year ON aeat_resources_metadata(fiscal_year);

COMMENT ON TABLE aeat_resources_metadata IS 'Метаданные ресурсов AEAT (формы, инструкции)';
COMMENT ON COLUMN aeat_resources_metadata.model_number IS 'Номер модели: Modelo 303, Modelo 111, etc.';

-- ============================================================
-- 7. Таблица: sync_logs
-- Логи синхронизации и обновления данных
-- ============================================================

CREATE TABLE sync_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES knowledge_sources(id) ON DELETE CASCADE,
    
    -- Синхронизация
    sync_started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sync_completed_at TIMESTAMPTZ,
    sync_duration_seconds INTEGER,
    sync_status TEXT NOT NULL CHECK (sync_status IN ('running', 'completed', 'failed', 'partial')),
    
    -- Статистика
    items_processed INTEGER DEFAULT 0,
    items_added INTEGER DEFAULT 0,
    items_updated INTEGER DEFAULT 0,
    items_deleted INTEGER DEFAULT 0,
    items_failed INTEGER DEFAULT 0,
    
    -- Ошибки
    error_message TEXT,
    error_details JSONB,
    
    -- Метаданные
    triggered_by TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sync_logs_source ON sync_logs(source_id);
CREATE INDEX idx_sync_logs_status ON sync_logs(sync_status);
CREATE INDEX idx_sync_logs_date ON sync_logs(sync_started_at);

COMMENT ON TABLE sync_logs IS 'Логи синхронизации и обновления данных';
COMMENT ON COLUMN sync_logs.triggered_by IS 'Кем запущена синхронизация: cron, manual, webhook';

-- ============================================================
-- Триггеры для обновления updated_at
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_knowledge_sources_updated_at BEFORE UPDATE ON knowledge_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_telegram_threads_updated_at BEFORE UPDATE ON telegram_threads_metadata
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pdf_documents_updated_at BEFORE UPDATE ON pdf_documents_metadata
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_news_articles_updated_at BEFORE UPDATE ON news_articles_metadata
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_calendar_deadlines_updated_at BEFORE UPDATE ON calendar_deadlines
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_aeat_resources_updated_at BEFORE UPDATE ON aeat_resources_metadata
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- Тестовые данные для инициализации источников
-- ============================================================

-- Добавляем источники Telegram
INSERT INTO knowledge_sources (source_type, source_name, source_url, description, sync_frequency, is_active)
VALUES 
    ('telegram', 'IT Autonomos Spain', 'https://t.me/it_autonomos_spain', 'Telegram группа для IT автономос в Испании', 'weekly', true),
    ('telegram', 'Digital Nomad Spain', 'https://t.me/chatfornomads', 'Telegram группа для цифровых кочевников в Испании', 'weekly', true);

-- Добавляем источники PDF
INSERT INTO knowledge_sources (source_type, source_name, description, sync_frequency, is_active)
VALUES 
    ('pdf', 'Spanish Tax Code', 'Налоговый кодекс Испании', 'manual', true),
    ('pdf', 'BOE Tax Laws', 'Налоговые законы из BOE', 'manual', true);

-- Добавляем источник календаря
INSERT INTO knowledge_sources (source_type, source_name, source_url, description, sync_frequency, is_active)
VALUES 
    ('calendar', 'AEAT Tax Calendar', 'https://sede.agenciatributaria.gob.es/Sede/calendario-contribuyente.html', 'Официальный налоговый календарь AEAT', 'monthly', true);

-- Добавляем источники новостей
INSERT INTO knowledge_sources (source_type, source_name, source_url, description, sync_frequency, is_active)
VALUES 
    ('news', 'Expansion Tax News', 'https://www.expansion.com/economia/fiscal.html', 'Новости о налогах от Expansion', 'daily', true),
    ('news', 'Cinco Dias Tax News', 'https://cincodias.elpais.com/noticias/fiscalidad/', 'Новости о налогах от Cinco Dias', 'daily', true);

-- Добавляем источники AEAT
INSERT INTO knowledge_sources (source_type, source_name, source_url, description, sync_frequency, is_active)
VALUES 
    ('aeat', 'AEAT Forms and Guides', 'https://sede.agenciatributaria.gob.es/', 'Формы и инструкции AEAT', 'monthly', true);

-- ============================================================
-- Представления для удобного доступа к данным
-- ============================================================

-- Представление: все активные источники с последними логами
CREATE OR REPLACE VIEW v_active_sources_with_logs AS
SELECT 
    ks.*,
    sl.sync_started_at AS last_sync_started,
    sl.sync_completed_at AS last_sync_completed,
    sl.sync_status AS last_sync_status,
    sl.items_processed AS last_sync_items_processed
FROM knowledge_sources ks
LEFT JOIN LATERAL (
    SELECT * FROM sync_logs 
    WHERE source_id = ks.id 
    ORDER BY sync_started_at DESC 
    LIMIT 1
) sl ON true
WHERE ks.is_active = true;

-- Представление: топ качественных Telegram тредов
CREATE OR REPLACE VIEW v_top_telegram_threads AS
SELECT 
    ttm.*,
    ks.source_name
FROM telegram_threads_metadata ttm
JOIN knowledge_sources ks ON ttm.source_id = ks.id
WHERE 
    ttm.is_deleted = false 
    AND ttm.indexed_in_elasticsearch = true
    AND ttm.quality_score >= 2.0
ORDER BY ttm.quality_score DESC, ttm.last_updated DESC;

-- Представление: актуальные налоговые дедлайны
CREATE OR REPLACE VIEW v_upcoming_deadlines AS
SELECT 
    cd.*,
    ks.source_name
FROM calendar_deadlines cd
JOIN knowledge_sources ks ON cd.source_id = ks.id
WHERE cd.deadline_date >= CURRENT_DATE
ORDER BY cd.deadline_date ASC;

-- ============================================================
-- Комментарии
-- ============================================================

COMMENT ON DATABASE postgres IS 'TuExpertoFiscal NAIL - Knowledge Base';

-- ============================================================
-- Developed by NAIL - Nahornyi AI Lab
-- ============================================================
