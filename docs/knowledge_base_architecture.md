# Архитектура базы знаний TuExpertoFiscal NAIL

## 📐 Общая концепция

### Принцип разделения данных:
- **Supabase (PostgreSQL)** - структурированные метаданные, версионирование, статусы
- **Elasticsearch** - полнотекстовый поиск, векторный поиск, гибридный поиск
- **Связь** - через уникальные идентификаторы

### Типы источников знаний:
1. **Telegram треды** - динамические диалоги (обновление: еженедельно)
2. **PDF документы** - законы и регламенты (обновление: по необходимости)
3. **Налоговый календарь** - структурированные даты (обновление: ежегодно)
4. **Новости** - актуальная информация (обновление: ежедневно)
5. **AEAT ресурсы** - официальные материалы (обновление: ежемесячно)
6. **Региональные документы** - Valencia, Catalunya и др. (обновление: по необходимости)

---

## 🗄️ Структура Supabase (PostgreSQL)

### 1. Таблица: `knowledge_sources`
**Назначение**: Реестр всех источников знаний

```sql
CREATE TABLE knowledge_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type TEXT NOT NULL, -- 'telegram', 'pdf', 'calendar', 'news', 'aeat', 'regional'
    source_name TEXT NOT NULL,
    source_url TEXT,
    description TEXT,
    language TEXT DEFAULT 'es',
    is_active BOOLEAN DEFAULT TRUE,
    last_synced_at TIMESTAMPTZ,
    next_sync_at TIMESTAMPTZ,
    sync_frequency TEXT, -- 'daily', 'weekly', 'monthly', 'manual'
    metadata JSONB, -- дополнительные параметры
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sources_type ON knowledge_sources(source_type);
CREATE INDEX idx_sources_active ON knowledge_sources(is_active);
```

---

### 2. Таблица: `telegram_threads_metadata`
**Назначение**: Метаданные Telegram тредов

```sql
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
    topics TEXT[], -- ['tax', 'visa', 'business']
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
    raw_data JSONB, -- полный JSON треда
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(thread_id, group_name)
);

CREATE INDEX idx_telegram_threads_source ON telegram_threads_metadata(source_id);
CREATE INDEX idx_telegram_threads_date ON telegram_threads_metadata(last_updated);
CREATE INDEX idx_telegram_threads_topics ON telegram_threads_metadata USING GIN(topics);
CREATE INDEX idx_telegram_threads_quality ON telegram_threads_metadata(quality_score);
CREATE INDEX idx_telegram_threads_elasticsearch ON telegram_threads_metadata(elasticsearch_doc_id);
```

---

### 3. Таблица: `pdf_documents_metadata`
**Назначение**: Метаданные PDF документов (законы, регламенты)

```sql
CREATE TABLE pdf_documents_metadata (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES knowledge_sources(id) ON DELETE CASCADE,
    
    -- Идентификаторы
    document_title TEXT NOT NULL,
    document_type TEXT NOT NULL, -- 'law', 'regulation', 'guide', 'form'
    document_number TEXT, -- номер закона/регламента
    
    -- Источник
    source_url TEXT NOT NULL,
    file_path TEXT, -- путь к загруженному файлу
    file_size_bytes BIGINT,
    file_hash TEXT, -- для проверки изменений
    
    -- Версионирование
    publication_date DATE,
    version_date DATE,
    version_number TEXT,
    is_latest_version BOOLEAN DEFAULT TRUE,
    superseded_by UUID REFERENCES pdf_documents_metadata(id),
    
    -- Характеристики
    page_count INTEGER,
    language TEXT DEFAULT 'es',
    region TEXT, -- 'national', 'valencia', 'catalunya', etc.
    
    -- Тематика
    categories TEXT[], -- ['irpf', 'iva', 'sociedades', 'autonomos']
    tags TEXT[],
    
    -- Обработка
    chunks_count INTEGER DEFAULT 0,
    processed_at TIMESTAMPTZ,
    processing_status TEXT DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'error'
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
```

---

### 4. Таблица: `news_articles_metadata`
**Назначение**: Метаданные новостных статей

```sql
CREATE TABLE news_articles_metadata (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES knowledge_sources(id) ON DELETE CASCADE,
    
    -- Идентификаторы
    article_url TEXT NOT NULL UNIQUE,
    article_title TEXT NOT NULL,
    
    -- Источник
    news_source TEXT NOT NULL, -- 'expansion', 'cincodias', etc.
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
```

---

### 5. Таблица: `calendar_deadlines`
**Назначение**: Структурированные налоговые дедлайны

```sql
CREATE TABLE calendar_deadlines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES knowledge_sources(id) ON DELETE CASCADE,
    
    -- Временные параметры
    deadline_date DATE NOT NULL,
    year INTEGER NOT NULL,
    quarter TEXT, -- 'Q1', 'Q2', 'Q3', 'Q4'
    month INTEGER,
    
    -- Налоговые характеристики
    tax_type TEXT NOT NULL, -- 'IRPF', 'IVA', 'Sociedades', 'Retenciones'
    tax_model TEXT, -- 'Modelo 303', 'Modelo 111', etc.
    description TEXT NOT NULL,
    
    -- Применимость
    applies_to TEXT[], -- ['autonomos', 'empresas', 'pymes', 'grandes_empresas']
    region TEXT DEFAULT 'national',
    
    -- Дополнительная информация
    payment_required BOOLEAN DEFAULT TRUE,
    declaration_required BOOLEAN DEFAULT TRUE,
    penalty_for_late TEXT,
    
    -- Уведомления
    reminder_sent_count INTEGER DEFAULT 0,
    last_reminder_sent_at TIMESTAMPTZ,
    
    -- Индексация (для контекстного поиска)
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
```

---

### 5b. Таблица: `calendar_events`
**Назначение**: Сырые события из официальных календарей AEAT (iCalendar)

```sql
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
```

**Ключевые моменты:**
- `calendar_type` — slug категории (например, `renta`, `iva`, `intrastat`).
- `is_active = false` для событий со статусом `CANCELLED`.
- `raw` сохраняет исходный блок VEVENT (аудит/диагностика).
- Таблица наполняется скриптом `sync_aeat_calendar.py` и служит источником для маппинга в `calendar_deadlines`.

---

### 6. Таблица: `aeat_resources_metadata`
**Назначение**: Метаданные ресурсов AEAT (формы, инструкции)

```sql
CREATE TABLE aeat_resources_metadata (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES knowledge_sources(id) ON DELETE CASCADE,
    
    -- Идентификаторы
    resource_url TEXT NOT NULL UNIQUE,
    resource_title TEXT NOT NULL,
    resource_type TEXT NOT NULL, -- 'form', 'guide', 'instruction', 'faq'
    
    -- Характеристики
    model_number TEXT, -- 'Modelo 303', 'Modelo 111', etc.
    fiscal_year INTEGER,
    language TEXT DEFAULT 'es',
    
    -- Версионирование
    version_date DATE,
    is_current_version BOOLEAN DEFAULT TRUE,
    
    -- Файлы
    file_path TEXT,
    file_format TEXT, -- 'pdf', 'html', 'xml'
    file_size_bytes BIGINT,
    
    -- Обработка
    processing_status TEXT DEFAULT 'pending',
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
```

---

### 7. Таблица: `sync_logs`
**Назначение**: Логи синхронизации и обновления данных

```sql
CREATE TABLE sync_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES knowledge_sources(id) ON DELETE CASCADE,
    
    -- Синхронизация
    sync_started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sync_completed_at TIMESTAMPTZ,
    sync_duration_seconds INTEGER,
    sync_status TEXT NOT NULL, -- 'running', 'completed', 'failed', 'partial'
    
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
    triggered_by TEXT, -- 'cron', 'manual', 'webhook'
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sync_logs_source ON sync_logs(source_id);
CREATE INDEX idx_sync_logs_status ON sync_logs(sync_status);
CREATE INDEX idx_sync_logs_date ON sync_logs(sync_started_at);
```

---

## 🔍 Структура Elasticsearch

### Индексы по типам источников:

#### 1. Индекс: `telegram_threads`
**Назначение**: Поиск по Telegram диалогам

```json
{
  "mappings": {
    "properties": {
      "thread_id": {"type": "keyword"},
      "group_name": {"type": "keyword"},
      "supabase_id": {"type": "keyword"},
      
      "content": {
        "type": "text",
        "analyzer": "standard",
        "fields": {
          "ru": {"type": "text", "analyzer": "russian"},
          "es": {"type": "text", "analyzer": "spanish"}
        }
      },
      "content_embedding": {
        "type": "dense_vector",
        "dims": 1536,
        "index": true,
        "similarity": "cosine"
      },
      
      "first_message": {"type": "text"},
      "last_message": {"type": "text"},
      "message_count": {"type": "integer"},
      
      "topics": {"type": "keyword"},
      "keywords": {"type": "keyword"},
      "tax_related": {"type": "boolean"},
      "visa_related": {"type": "boolean"},
      "business_related": {"type": "boolean"},
      
      "quality_score": {"type": "float"},
      "first_message_date": {"type": "date"},
      "last_updated": {"type": "date"},
      
      "indexed_at": {"type": "date"}
    }
  }
}
```

#### 2. Индекс: `pdf_documents`
**Назначение**: Поиск по PDF документам (чанки)

```json
{
  "mappings": {
    "properties": {
      "document_id": {"type": "keyword"},
      "chunk_id": {"type": "keyword"},
      "supabase_id": {"type": "keyword"},
      
      "content": {
        "type": "text",
        "analyzer": "spanish",
        "fields": {
          "exact": {"type": "text", "analyzer": "standard"}
        }
      },
      "content_embedding": {
        "type": "dense_vector",
        "dims": 1536,
        "index": true,
        "similarity": "cosine"
      },
      
      "document_title": {"type": "text"},
      "document_type": {"type": "keyword"},
      "document_number": {"type": "keyword"},
      
      "chunk_index": {"type": "integer"},
      "page_number": {"type": "integer"},
      
      "categories": {"type": "keyword"},
      "region": {"type": "keyword"},
      "publication_date": {"type": "date"},
      
      "indexed_at": {"type": "date"}
    }
  }
}
```

#### 3. Индекс: `news_articles`
**Назначение**: Поиск по новостным статьям

```json
{
  "mappings": {
    "properties": {
      "article_id": {"type": "keyword"},
      "supabase_id": {"type": "keyword"},
      
      "title": {
        "type": "text",
        "analyzer": "spanish",
        "fields": {
          "exact": {"type": "keyword"}
        }
      },
      "content": {"type": "text", "analyzer": "spanish"},
      "summary": {"type": "text", "analyzer": "spanish"},
      "content_embedding": {
        "type": "dense_vector",
        "dims": 1536,
        "index": true,
        "similarity": "cosine"
      },
      
      "news_source": {"type": "keyword"},
      "author": {"type": "keyword"},
      
      "categories": {"type": "keyword"},
      "keywords": {"type": "keyword"},
      "tax_related": {"type": "boolean"},
      
      "published_at": {"type": "date"},
      "relevance_score": {"type": "float"},
      
      "indexed_at": {"type": "date"}
    }
  }
}
```

#### 4. Индекс: `calendar_deadlines`
**Назначение**: Поиск по налоговым дедлайнам

```json
{
  "mappings": {
    "properties": {
      "deadline_id": {"type": "keyword"},
      "supabase_id": {"type": "keyword"},
      
      "description": {"type": "text", "analyzer": "spanish"},
      "content_embedding": {
        "type": "dense_vector",
        "dims": 1536,
        "index": true,
        "similarity": "cosine"
      },
      
      "deadline_date": {"type": "date"},
      "year": {"type": "integer"},
      "quarter": {"type": "keyword"},
      
      "tax_type": {"type": "keyword"},
      "tax_model": {"type": "keyword"},
      "applies_to": {"type": "keyword"},
      
      "indexed_at": {"type": "date"}
    }
  }
}
```

#### 5. Индекс: `aeat_resources`
**Назначение**: Поиск по ресурсам AEAT

```json
{
  "mappings": {
    "properties": {
      "resource_id": {"type": "keyword"},
      "supabase_id": {"type": "keyword"},
      
      "title": {"type": "text", "analyzer": "spanish"},
      "content": {"type": "text", "analyzer": "spanish"},
      "content_embedding": {
        "type": "dense_vector",
        "dims": 1536,
        "index": true,
        "similarity": "cosine"
      },
      
      "resource_type": {"type": "keyword"},
      "model_number": {"type": "keyword"},
      "fiscal_year": {"type": "integer"},
      
      "indexed_at": {"type": "date"}
    }
  }
}
```

---

## 🔄 Стратегии обновления данных

### 1. Telegram треды (еженедельно)

```python
def update_telegram_threads():
    # 1. Скачать новые сообщения за последнюю неделю
    new_messages = download_weekly_telegram_messages()
    
    # 2. Обновить существующие треды или создать новые
    for thread in new_messages:
        # Проверить существует ли тред в Supabase
        existing = db.query("telegram_threads_metadata")
            .filter("thread_id", thread_id)
            .single()
        
        if existing:
            # Обновить существующий
            db.update("telegram_threads_metadata", {
                "last_updated": thread.last_updated,
                "message_count": thread.message_count,
                "raw_data": thread.to_json(),
                "version": existing.version + 1
            }).eq("id", existing.id)
            
            # Обновить в Elasticsearch
            es.update(index="telegram_threads", 
                     id=existing.elasticsearch_doc_id,
                     body={"doc": prepare_for_elasticsearch(thread)})
        else:
            # Создать новый
            supabase_id = db.insert("telegram_threads_metadata", {
                "thread_id": thread.thread_id,
                "group_name": thread.group_name,
                # ... другие поля
            })
            
            # Индексировать в Elasticsearch
            es_doc_id = es.index(index="telegram_threads",
                                 body=prepare_for_elasticsearch(thread))
            
            # Обновить связь
            db.update("telegram_threads_metadata", {
                "elasticsearch_doc_id": es_doc_id,
                "indexed_in_elasticsearch": True
            }).eq("id", supabase_id)
```

### 2. PDF документы (по необходимости)

```python
def update_pdf_documents():
    # 1. Проверить изменения документов
    documents = get_pdf_sources()
    
    for doc_source in documents:
        # Скачать документ
        file_path = download_pdf(doc_source.url)
        file_hash = calculate_hash(file_path)
        
        # Проверить существует ли
        existing = db.query("pdf_documents_metadata")
            .filter("source_url", doc_source.url)
            .single()
        
        if existing and existing.file_hash == file_hash:
            # Документ не изменился
            continue
        
        # Обработать документ
        chunks = process_pdf_document(file_path)
        
        # Сохранить метаданные в Supabase
        supabase_id = db.upsert("pdf_documents_metadata", {
            "document_title": doc_source.title,
            "source_url": doc_source.url,
            "file_hash": file_hash,
            "chunks_count": len(chunks),
            "processing_status": "completed"
        })
        
        # Удалить старые чанки из Elasticsearch
        if existing:
            es.delete_by_query(index="pdf_documents",
                              query={"match": {"document_id": existing.id}})
        
        # Индексировать новые чанки
        for chunk in chunks:
            es.index(index="pdf_documents", body={
                "document_id": supabase_id,
                "supabase_id": supabase_id,
                "content": chunk.text,
                "content_embedding": generate_embedding(chunk.text),
                # ... другие поля
            })
```

### 3. Новости (ежедневно)

```python
def update_news_articles():
    # 1. Скрапить новости за последние 24 часа
    articles = scrape_news_sites()
    
    for article in articles:
        # Проверить существует ли
        existing = db.query("news_articles_metadata")
            .filter("article_url", article.url)
            .single()
        
        if existing:
            # Новость уже есть
            continue
        
        # Проверить релевантность
        is_relevant = check_relevance(article.content)
        
        if not is_relevant:
            continue
        
        # Сохранить в Supabase
        supabase_id = db.insert("news_articles_metadata", {
            "article_url": article.url,
            "article_title": article.title,
            "news_source": article.source,
            "published_at": article.published_at,
            "relevance_score": article.relevance_score
        })
        
        # Индексировать в Elasticsearch
        es_doc_id = es.index(index="news_articles", body={
            "article_id": article.url,
            "supabase_id": supabase_id,
            "title": article.title,
            "content": article.content,
            "content_embedding": generate_embedding(article.content),
            # ... другие поля
        })
        
        # Обновить связь
        db.update("news_articles_metadata", {
            "elasticsearch_doc_id": es_doc_id,
            "indexed_in_elasticsearch": True
        }).eq("id", supabase_id)
```

### 4. Налоговый календарь (ежегодно)

```python
def update_tax_calendar():
    # 1. Скрапить календарь AEAT на следующий год
    deadlines = scrape_aeat_calendar(year=2026)
    
    for deadline in deadlines:
        # Проверить существует ли
        existing = db.query("calendar_deadlines")
            .filter("deadline_date", deadline.date)
            .filter("tax_type", deadline.tax_type)
            .single()
        
        if existing:
            # Обновить если изменилось
            db.update("calendar_deadlines", {
                "description": deadline.description,
                "applies_to": deadline.applies_to
            }).eq("id", existing.id)
        else:
            # Создать новый
            supabase_id = db.insert("calendar_deadlines", {
                "deadline_date": deadline.date,
                "year": deadline.year,
                "tax_type": deadline.tax_type,
                "description": deadline.description
            })
            
            # Индексировать в Elasticsearch
            es.index(index="calendar_deadlines", body={
                "deadline_id": supabase_id,
                "supabase_id": supabase_id,
                "description": deadline.description,
                "content_embedding": generate_embedding(deadline.description),
                # ... другие поля
            })
```

---

## 🔎 Стратегии извлечения данных

### 1. Гибридный поиск по всем источникам

```python
def search_knowledge_base(query: str, filters: dict = None):
    # Генерируем embedding для запроса
    query_embedding = generate_embedding(query)
    
    # Определяем тематику запроса
    query_type = classify_query(query)  # 'tax', 'visa', 'business', 'calendar'
    
    # Поиск в разных индексах с разными весами
    results = []
    
    # 1. Поиск в Telegram тредах (вес 0.3)
    if query_type in ['tax', 'visa', 'business']:
        telegram_results = es.search(index="telegram_threads", body={
            "query": {
                "bool": {
                    "should": [
                        # Векторный поиск
                        {
                            "knn": {
                                "field": "content_embedding",
                                "query_vector": query_embedding,
                                "k": 5,
                                "boost": 0.7
                            }
                        },
                        # BM25 поиск
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["content^2", "first_message"],
                                "boost": 0.3
                            }
                        }
                    ],
                    "filter": [
                        {"term": {f"{query_type}_related": True}},
                        {"range": {"quality_score": {"gte": 2.0}}}
                    ]
                }
            },
            "size": 5
        })
        results.extend(telegram_results["hits"]["hits"])
    
    # 2. Поиск в PDF документах (вес 0.4)
    pdf_results = es.search(index="pdf_documents", body={
        "query": {
            "bool": {
                "should": [
                    {
                        "knn": {
                            "field": "content_embedding",
                            "query_vector": query_embedding,
                            "k": 5,
                            "boost": 0.8
                        }
                    },
                    {
                        "match": {
                            "content": {
                                "query": query,
                                "boost": 0.2
                            }
                        }
                    }
                ]
            }
        },
        "size": 5
    })
    results.extend(pdf_results["hits"]["hits"])
    
    # 3. Поиск в новостях (вес 0.2)
    news_results = es.search(index="news_articles", body={
        "query": {
            "bool": {
                "should": [
                    {
                        "knn": {
                            "field": "content_embedding",
                            "query_vector": query_embedding,
                            "k": 3,
                            "boost": 0.7
                        }
                    },
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^2", "content"],
                            "boost": 0.3
                        }
                    }
                ],
                "filter": [
                    {"range": {"published_at": {"gte": "now-90d"}}}
                ]
            }
        },
        "size": 3
    })
    results.extend(news_results["hits"]["hits"])
    
    # 4. Поиск в календаре (вес 0.1)
    if "когда" in query.lower() or "срок" in query.lower() or "дедлайн" in query.lower():
        calendar_results = es.search(index="calendar_deadlines", body={
            "query": {
                "bool": {
                    "should": [
                        {
                            "knn": {
                                "field": "content_embedding",
                                "query_vector": query_embedding,
                                "k": 2
                            }
                        },
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["description", "tax_type"]
                            }
                        }
                    ],
                    "filter": [
                        {"range": {"deadline_date": {"gte": "now"}}}
                    ]
                }
            },
            "size": 2
        })
        results.extend(calendar_results["hits"]["hits"])
    
    # Ранжируем и возвращаем топ результатов
    ranked_results = rank_results(results, query_type)
    return ranked_results[:10]
```

### 2. Получение метаданных из Supabase

```python
def enrich_search_results(results):
    """Обогащаем результаты метаданными из Supabase"""
    enriched = []
    
    for result in results:
        supabase_id = result["_source"]["supabase_id"]
        index_name = result["_index"]
        
        # Получаем метаданные в зависимости от индекса
        if index_name == "telegram_threads":
            metadata = db.query("telegram_threads_metadata")
                .select("*")
                .eq("id", supabase_id)
                .single()
        elif index_name == "pdf_documents":
            metadata = db.query("pdf_documents_metadata")
                .select("*")
                .eq("id", supabase_id)
                .single()
        elif index_name == "news_articles":
            metadata = db.query("news_articles_metadata")
                .select("*")
                .eq("id", supabase_id)
                .single()
        elif index_name == "calendar_deadlines":
            metadata = db.query("calendar_deadlines")
                .select("*")
                .eq("id", supabase_id)
                .single()
        
        enriched.append({
            "content": result["_source"]["content"],
            "score": result["_score"],
            "metadata": metadata,
            "source_type": index_name
        })
    
    return enriched
```

---

## 📊 Диаграмма архитектуры

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA SOURCES                              │
├─────────────┬──────────────┬──────────────┬─────────────────┤
│  Telegram   │   PDF Docs   │    News      │  Tax Calendar   │
│   Groups    │   (Laws)     │   Scrapers   │     (AEAT)      │
└──────┬──────┴──────┬───────┴──────┬───────┴────────┬─────────┘
       │             │              │                │
       ▼             ▼              ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│              INGESTION SCRIPTS (Python)                      │
│  • Weekly Telegram Parser                                    │
│  • PDF Document Processor                                    │
│  • Daily News Scraper                                        │
│  • Annual Calendar Updater                                   │
└─────────┬────────────────────────┬──────────────────────────┘
          │                        │
          ▼                        ▼
┌─────────────────────┐   ┌────────────────────────────┐
│   SUPABASE          │   │   ELASTICSEARCH            │
│   (PostgreSQL)      │   │   (Search Engine)          │
├─────────────────────┤   ├────────────────────────────┤
│ • Metadata          │   │ • Full-text search         │
│ • Versioning        │   │ • Vector search (kNN)      │
│ • Relationships     │   │ • Hybrid search            │
│ • Sync status       │   │ • Fast retrieval           │
│ • Structured data   │   │ • Relevance ranking        │
└─────────┬───────────┘   └────────────┬───────────────┘
          │                            │
          └──────────┬─────────────────┘
                     ▼
          ┌─────────────────────┐
          │   SEARCH SERVICE    │
          │    (Python API)     │
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │   RAG PIPELINE      │
          │  (LangChain + LLM)  │
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │   TELEGRAM BOT      │
          │   (User Interface)  │
          └─────────────────────┘
```

---

## ✅ Преимущества архитектуры

1. **Разделение ответственности**: Supabase для структуры, Elasticsearch для поиска
2. **Масштабируемость**: Каждый источник индексируется отдельно
3. **Версионирование**: Отслеживаем изменения документов
4. **Гибкость поиска**: Гибридный поиск по нескольким источникам
5. **Мониторинг**: Логи синхронизации для отладки
6. **Обогащение контекста**: Метаданные из Supabase + контент из Elasticsearch

---

*Разработано NAIL - Nahornyi AI Lab*
