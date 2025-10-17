# Архитектура базы знаний - Краткое руководство

## 🎯 Основная концепция

### Два хранилища:

**Supabase (PostgreSQL)** → Структурированные метаданные
- ID документов
- Версии
- Статусы обработки
- Связи между источниками
- Логи синхронизации

**Elasticsearch** → Поисковый контент
- Полный текст для поиска
- Векторные embeddings
- Быстрый гибридный поиск
- Ранжирование результатов

### Связь между системами:
Каждый документ имеет:
- `id` в Supabase (источник правды)
- `elasticsearch_doc_id` (ссылка на поисковый индекс)

---

## 📦 Источники данных и таблицы

### 1. Telegram треды → `telegram_threads_metadata`

**Что храним в Supabase:**
```sql
{
  "thread_id": 21565,
  "group_name": "IT Autonomos Spain",
  "message_count": 20,
  "quality_score": 5.0,
  "topics": ["tax", "visa", "business"],
  "keywords": ["автономо", "налог", "ss"],
  "tax_related": true,
  "elasticsearch_doc_id": "it_autonomos_21565",
  "raw_data": {...}  -- полный JSON треда
}
```

**Что храним в Elasticsearch:**
```json
{
  "supabase_id": "uuid-xxx",
  "content": "Весь текст всех сообщений...",
  "content_embedding": [0.123, 0.456, ...],
  "first_message": "Текст первого сообщения...",
  "topics": ["tax", "visa"],
  "quality_score": 5.0
}
```

**Обновление:** Еженедельно (cron)
- Скачиваем новые сообщения за неделю
- Обновляем существующие треды или создаём новые
- Переиндексируем в Elasticsearch

---

### 2. PDF документы → `pdf_documents_metadata`

**Что храним в Supabase:**
```sql
{
  "document_title": "Ley 35/2006 IRPF",
  "document_type": "law",
  "source_url": "https://...",
  "file_hash": "sha256...",
  "is_latest_version": true,
  "chunks_count": 245,
  "processing_status": "completed",
  "categories": ["irpf", "autonomos"]
}
```

**Что храним в Elasticsearch:**
- Каждый чанк документа как отдельный документ
- Все чанки связаны через `document_id`

```json
{
  "document_id": "uuid-xxx",
  "chunk_id": "uuid-yyy",
  "supabase_id": "uuid-xxx",
  "content": "Текст чанка...",
  "content_embedding": [0.123, ...],
  "chunk_index": 5,
  "page_number": 12,
  "document_title": "Ley 35/2006 IRPF"
}
```

**Обновление:** По необходимости (manual)
- Проверяем hash файла
- Если изменился → переобрабатываем
- Удаляем старые чанки из Elasticsearch
- Индексируем новые

---

### 3. Новости → `news_articles_metadata`

**Что храним в Supabase:**
```sql
{
  "article_url": "https://...",
  "article_title": "Cambios en IRPF 2025",
  "news_source": "Expansion",
  "published_at": "2025-10-01",
  "relevance_score": 0.85,
  "categories": ["irpf", "cambios_legislativos"],
  "is_relevant": true
}
```

**Что храним в Elasticsearch:**
```json
{
  "supabase_id": "uuid-xxx",
  "title": "Cambios en IRPF 2025",
  "content": "Полный текст статьи...",
  "content_embedding": [0.123, ...],
  "published_at": "2025-10-01",
  "news_source": "Expansion"
}
```

**Обновление:** Ежедневно (cron)
- Скрапим новости за последние 24 часа
- Проверяем релевантность через LLM
- Индексируем только релевантные

---

### 4. Налоговый календарь → `calendar_deadlines`

**Что храним в Supabase:**
```sql
{
  "deadline_date": "2025-10-20",
  "tax_type": "IVA",
  "tax_model": "Modelo 303",
  "description": "IVA квартальный за Q3 2025",
  "applies_to": ["autonomos", "empresas"],
  "quarter": "Q3",
  "year": 2025
}
```

**Что храним в Elasticsearch:**
```json
{
  "supabase_id": "uuid-xxx",
  "description": "IVA квартальный за Q3 2025...",
  "content_embedding": [0.123, ...],
  "deadline_date": "2025-10-20",
  "tax_type": "IVA",
  "applies_to": ["autonomos"]
}
```

**Обновление:** Ежегодно + ежемесячная проверка
- Скрапим календарь AEAT
- Обновляем даты на следующий год
- Отправляем напоминания

---

### 4b. AEAT iCalendar (сырые события) → `calendar_events`

**Что храним в Supabase:**
```json
{
  "uid": "event-uuid",
  "calendar_type": "iva",
  "summary": "Presentación modelo 303",
  "dtstart": "2025-03-20T09:00:00+01:00",
  "status": "CONFIRMED",
  "sequence": 3,
  "is_active": true,
  "raw": "BEGIN:VEVENT...END:VEVENT"
}
```

**Зачем:**
- Поддерживать точную копию официальных .ics (Google Calendar) AEAT.
- Трекать изменения `STATUS`/`SEQUENCE` и отмены (`STATUS:CANCELLED`).
- Источник правды для последующей нормализации в `calendar_deadlines` и для уведомлений.

**Скрипт:** `python scripts/ingestion/sync_aeat_calendar.py`

**Обновление:** Еженедельно (cron / GitHub Actions) — перезаписать события и зафиксировать изменения.

---

## 🔄 Стратегии обновления

### 1. Telegram (еженедельно - каждое воскресенье 2:00)

```bash
# Cron: 0 2 * * 0
python scripts/telegram/update_threads_weekly.py
```

**Алгоритм:**
1. Загружаем новые сообщения за последние 7 дней
2. Для каждого треда:
   - Проверяем есть ли в `telegram_threads_metadata`
   - Если есть → обновляем (`version++`)
   - Если нет → создаём новый
3. Обновляем в Elasticsearch:
   - Если тред существует → `es.update()`
   - Если новый → `es.index()`
4. Логируем в `sync_logs`

---

### 2. Новости (ежедневно - каждый день 6:00)

```bash
# Cron: 0 6 * * *
python scripts/ingestion/ingest_news_daily.py
```

**Алгоритм:**
1. Скрапим новости с 5-7 источников за последние 24 часа
2. Проверяем дубликаты по `article_url`
3. Фильтруем релевантность через LLM (gemini-1.5-flash)
4. Сохраняем в Supabase только релевантные
5. Индексируем в Elasticsearch
6. Логируем в `sync_logs`

---

### 3. PDF документы (по запросу)

```bash
# Manual или по событию (webhook когда закон обновляется)
python scripts/ingestion/ingest_pdf_documents.py --source-id <uuid>
```

**Алгоритм:**
1. Скачиваем PDF файл
2. Вычисляем hash
3. Проверяем изменился ли (`file_hash != old_hash`)
4. Если изменился:
   - Обрабатываем PDF → чанки
   - Генерируем embeddings
   - Удаляем старые чанки из Elasticsearch
   - Индексируем новые
   - Обновляем метаданные в Supabase
5. Логируем в `sync_logs`

---

### 4. Календарь (ежемесячно - 1-го числа 3:00)

```bash
# Cron: 0 3 1 * *
python scripts/ingestion/update_tax_calendar.py
```

**Алгоритм:**
1. Скрапим календарь AEAT
2. Извлекаем даты на текущий + следующий год
3. Для каждого дедлайна:
   - Проверяем есть ли в `calendar_deadlines`
   - Обновляем или создаём
4. Индексируем в Elasticsearch (для контекстного поиска)
5. Настраиваем напоминания

---

## 🔎 Как извлекаем данные

### Пример поиска: "Когда платить IVA автономос?"

#### 1. Определяем тип запроса
```python
query_type = classify_query("Когда платить IVA автономос?")
# Результат: "calendar" + "tax"
```

#### 2. Ищем в нескольких индексах параллельно

**A. Поиск в календаре** (вес 0.5)
```python
calendar_results = es.search(index="calendar_deadlines", body={
    "query": {
        "bool": {
            "should": [
                {"knn": {"field": "content_embedding", "query_vector": embedding, "k": 3}},
                {"match": {"description": "IVA автономос"}}
            ],
            "filter": [
                {"term": {"tax_type": "IVA"}},
                {"term": {"applies_to": "autonomos"}},
                {"range": {"deadline_date": {"gte": "now"}}}
            ]
        }
    }
})
```

**B. Поиск в Telegram** (вес 0.3)
```python
telegram_results = es.search(index="telegram_threads", body={
    "query": {
        "bool": {
            "should": [
                {"knn": {"field": "content_embedding", "query_vector": embedding, "k": 5}},
                {"multi_match": {"query": "IVA автономос", "fields": ["content", "first_message"]}}
            ],
            "filter": [
                {"term": {"tax_related": True}},
                {"range": {"quality_score": {"gte": 2.0}}}
            ]
        }
    }
})
```

**C. Поиск в PDF** (вес 0.2)
```python
pdf_results = es.search(index="pdf_documents", body={
    "query": {
        "bool": {
            "should": [
                {"knn": {"field": "content_embedding", "query_vector": embedding, "k": 3}},
                {"match": {"content": "IVA"}}
            ],
            "filter": [
                {"terms": {"categories": ["iva", "autonomos"]}}
            ]
        }
    }
})
```

#### 3. Объединяем и ранжируем результаты

```python
# Применяем веса
calendar_weighted = [r for r in calendar_results with weight=0.5]
telegram_weighted = [r for r in telegram_results with weight=0.3]
pdf_weighted = [r for r in pdf_results with weight=0.2]

# Объединяем
all_results = calendar_weighted + telegram_weighted + pdf_weighted

# Сортируем по итоговому score
ranked_results = sorted(all_results, key=lambda x: x.final_score, reverse=True)[:10]
```

#### 4. Обогащаем метаданными из Supabase

```python
enriched_results = []
for result in ranked_results:
    # Получаем метаданные
    if result.index == "calendar_deadlines":
        metadata = supabase.table("calendar_deadlines").select("*").eq("id", result.supabase_id).single()
    elif result.index == "telegram_threads":
        metadata = supabase.table("telegram_threads_metadata").select("*").eq("id", result.supabase_id).single()
    # ...
    
    enriched_results.append({
        "content": result.content,
        "score": result.final_score,
        "source_type": result.index,
        "metadata": metadata
    })
```

#### 5. Передаём в LLM как контекст

```python
context = format_context_for_llm(enriched_results)

llm_response = llm.generate(f"""
Контекст:
{context}

Вопрос пользователя: Когда платить IVA автономос?

Ответь точно и с указанием источников.
""")
```

---

## 📊 Преимущества архитектуры

### ✅ Разделение ответственности
- **Supabase**: Метаданные, версионирование, логи
- **Elasticsearch**: Быстрый поиск, ранжирование

### ✅ Масштабируемость
- Каждый источник в отдельной таблице
- Легко добавить новый источник
- Параллельный поиск по индексам

### ✅ Версионирование
- Отслеживаем изменения документов
- История обновлений в `sync_logs`
- Можем откатить изменения

### ✅ Гибкость поиска
- Гибридный поиск (semantic + BM25)
- Фильтрация по метаданным
- Взвешенные результаты из разных источников

### ✅ Мониторинг
- Логи всех синхронизаций
- Статусы обработки
- Ошибки и их детали

---

## 🚀 Следующие шаги

1. **Развернуть схему в Supabase**
   ```bash
   psql -h supabase_url -d postgres < database/knowledge_base_schema.sql
   ```

2. **Создать индексы в Elasticsearch**
   - Настроить mappings для каждого индекса
   - Включить kNN search для embeddings

3. **Реализовать скрипты синхронизации**
   - Telegram: еженедельный парсер
   - Новости: ежедневный скрапер
   - PDF: процессор по запросу
   - Календарь: ежемесячный обновлятор

4. **Настроить cron jobs на сервере**
   - Автоматизация обновлений
   - Мониторинг логов

5. **Интегрировать с RAG pipeline**
   - Unified search service
   - Context enrichment
   - Source citation

---

*Разработано NAIL - Nahornyi AI Lab*
