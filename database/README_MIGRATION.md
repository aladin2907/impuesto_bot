# Миграция базы данных на pgvector

## Обзор

Миграция с Elasticsearch на Supabase PostgreSQL + pgvector для векторного поиска.

## Новая архитектура

### Таблицы с векторами:

1. **telegram_threads_content** - Telegram треды с эмбеддингами
   - `content_embedding` - vector(1024) от multilingual-e5-large
   - Гибридный поиск: kNN + Full-Text Search

2. **pdf_documents_content** - PDF чанки с эмбеддингами
   - `content_embedding` - vector(1536) от OpenAI text-embedding-3-small
   - Гибридный поиск: kNN + Full-Text Search

3. **news_articles_content** - Новостные статьи с эмбеддингами
   - `content_embedding` - vector(1536) от OpenAI
   - Гибридный поиск: kNN + Full-Text Search

4. **calendar_deadlines** - Налоговые дедлайны
   - Без векторов (только Full-Text Search)
   - Структурированные данные

## Шаги миграции

### 1. Подготовка Supabase

Зайдите в Supabase Dashboard → SQL Editor

#### 1.1. Включите pgvector расширение:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

#### 1.2. Проверьте версию:

```sql
SELECT extversion FROM pg_extension WHERE extname = 'vector';
-- Должна быть >= 0.5.0
```

### 2. Создание новой схемы

#### Вариант A: Через Supabase Dashboard (рекомендуется)

1. Откройте [database/vector_schema.sql](vector_schema.sql)
2. Скопируйте весь SQL код
3. Вставьте в Supabase SQL Editor
4. Нажмите "Run"

#### Вариант B: Через psql (локально)

```bash
psql -h your-supabase-host \
     -U postgres \
     -d postgres \
     -f database/vector_schema.sql
```

### 3. Миграция старых данных (опционально)

Если у вас уже есть данные в старых таблицах:

```bash
psql -h your-supabase-host \
     -U postgres \
     -d postgres \
     -f database/migrations/001_migrate_to_vector_schema.sql
```

⚠️ **Важно**: Скрипт миграции:
- Переименует старые таблицы в `*_old`
- Удалит Elasticsearch-специфичные поля
- НЕ удалит старые данные автоматически (нужно сделать вручную после проверки)

### 4. Генерация векторов

Векторы нужно сгенерировать отдельно через Python скрипты:

```bash
# Генерация векторов для Telegram (HuggingFace API)
python scripts/ingestion/generate_telegram_embeddings.py

# Генерация векторов для PDF (OpenAI API)
python scripts/ingestion/generate_pdf_embeddings.py

# Генерация векторов для News (OpenAI API)
python scripts/ingestion/generate_news_embeddings.py
```

*(Эти скрипты будут созданы далее)*

### 5. Проверка миграции

#### Проверьте создание таблиц:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_name IN (
    'telegram_threads_content',
    'pdf_documents_content',
    'news_articles_content',
    'calendar_deadlines'
);
```

#### Проверьте векторные индексы:

```sql
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname LIKE '%embedding%';
```

#### Проверьте статистику:

```sql
SELECT * FROM v_vector_store_stats;
```

### 6. Тестирование поиска

#### Тест гибридного поиска в Telegram:

```sql
SELECT *
FROM search_telegram_hybrid(
    'какой налог для автономос?',
    '[0.1, 0.2, ...]'::vector(1024),  -- замените на реальный вектор
    10,
    0.5
);
```

#### Тест гибридного поиска в PDF:

```sql
SELECT *
FROM search_pdf_hybrid(
    'modelo 303',
    '[0.1, 0.2, ...]'::vector(1536),  -- замените на реальный вектор
    10,
    0.5
);
```

#### Тест keyword поиска в календаре:

```sql
SELECT *
FROM calendar_deadlines
WHERE to_tsvector('spanish', description) @@ plainto_tsquery('spanish', 'IVA')
ORDER BY deadline_date
LIMIT 10;
```

## Индексы и производительность

### Векторные индексы (HNSW)

Мы используем **HNSW** (Hierarchical Navigable Small World) вместо IVFFlat:

- ✅ Быстрее поиск
- ✅ Лучшее качество (recall)
- ❌ Медленнее построение индекса
- ❌ Больше памяти

Параметры HNSW:
- `m = 16` - количество связей (trade-off: скорость/качество)
- `ef_construction = 64` - точность построения

### Полнотекстовые индексы (GIN)

Используем испанскую конфигурацию:
```sql
to_tsvector('spanish', content)
```

## Размеры векторов

| Источник | Модель | Размерность | API |
|----------|--------|-------------|-----|
| Telegram | multilingual-e5-large | 1024 | HuggingFace |
| PDF | text-embedding-3-small | 1536 | OpenAI |
| News | text-embedding-3-small | 1536 | OpenAI |

## Оценка хранилища

Для 10,000 документов:

```
Telegram: 10,000 × (1024 × 4 bytes) ≈ 40 MB векторов
PDF:      10,000 × (1536 × 4 bytes) ≈ 60 MB векторов
News:      5,000 × (1536 × 4 bytes) ≈ 30 MB векторов
---------------------------------------------------
Итого: ~130 MB только векторы
```

Общий размер БД с текстом: **~500 MB - 1 GB**

## Откат миграции

Если что-то пошло не так:

```sql
-- Вернуть старые таблицы
ALTER TABLE telegram_threads_content RENAME TO telegram_threads_content_new;
ALTER TABLE telegram_threads_metadata_old RENAME TO telegram_threads_metadata;

-- Удалить новые таблицы
DROP TABLE IF EXISTS telegram_threads_content_new CASCADE;
DROP TABLE IF EXISTS pdf_documents_content CASCADE;
DROP TABLE IF EXISTS news_articles_content CASCADE;

-- Удалить функции
DROP FUNCTION IF EXISTS search_telegram_hybrid CASCADE;
DROP FUNCTION IF EXISTS search_pdf_hybrid CASCADE;
```

## Полезные запросы

### Посмотреть размер таблиц:

```sql
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Посмотреть размер индексов:

```sql
SELECT
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) AS size
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexname::regclass) DESC;
```

### Пересоздать векторный индекс:

```sql
-- Удалить старый
DROP INDEX idx_telegram_content_embedding;

-- Создать новый (может занять время!)
CREATE INDEX idx_telegram_content_embedding ON telegram_threads_content
USING hnsw (content_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

## Troubleshooting

### Ошибка: "extension vector does not exist"

```sql
CREATE EXTENSION vector;
```

Если не помогло - обратитесь в поддержку Supabase (pgvector должен быть доступен)

### Ошибка: "operator does not exist: vector <=> vector"

Пересоздайте расширение:
```sql
DROP EXTENSION vector CASCADE;
CREATE EXTENSION vector;
```

### Медленный поиск

1. Проверьте, что индексы созданы:
   ```sql
   \d telegram_threads_content
   ```

2. Увеличьте `ef_search` для лучшего качества:
   ```sql
   SET hnsw.ef_search = 100;
   ```

3. Проанализируйте план запроса:
   ```sql
   EXPLAIN ANALYZE
   SELECT * FROM telegram_threads_content
   ORDER BY content_embedding <=> '[...]'::vector
   LIMIT 10;
   ```

## Следующие шаги

После успешной миграции БД:

1. ✅ Создать Python классы для работы с векторами
2. ✅ Реализовать сервисы поиска
3. ✅ Написать скрипты генерации эмбеддингов
4. ✅ Протестировать производительность
5. ✅ Обновить документацию API

---

*Документация обновлена: 2025-12-04*
