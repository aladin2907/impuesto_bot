# Search Service Fix - 2025-10-26

## Проблема

Поиск возвращал пустые результаты, несмотря на то, что:
- Elasticsearch был подключен
- Данные были в индексах (75k+ telegram, 4k+ pdf)

## Причина

**Несовпадение названий полей** между кодом и реальной структурой индексов в Elasticsearch.

### Что было в коде:
```python
"fields": ["text", "title", "content"]  # ❌ Неправильно
```

### Что реально в индексе:
```python
# pdf_documents
"fields": ["content", "document_title", "categories"]

# telegram_threads  
"fields": ["content", "first_message", "topics", "keywords"]
```

## Решение

Обновлены все методы поиска в `app/services/search_service.py`:

### 1. `_search_pdf()` (строки 432-479)
- ✅ Изменено: `["content^2", "document_title", "categories"]`
- ✅ Добавлено: правильные метаданные (document_id, document_type, chunk_index)
- ✅ Добавлено: обрезка текста до 500 символов
- ✅ Добавлено: логирование результатов

### 2. `_search_telegram()` (строки 380-430)
- ✅ Изменено: `["content^2", "first_message", "last_message", "topics", "keywords"]`
- ✅ Добавлено: thread_id, message_count, quality_score в метаданные
- ✅ Добавлено: fallback на first_message если content пустой

### 3. `_search_calendar()` (строки 481-522)
- ✅ Изменено: `["description", "tax_type", "deadline_date"]`
- ✅ Добавлено: quarter, applies_to в метаданные

### 4. `_search_news()` (строки 524-568)
- ✅ Изменено: `["content^2", "article_title", "categories"]`
- ✅ Добавлено: article_url, news_source, published_at в метаданные

### 5. `_search_aeat()` (строки 570-614)
- ✅ Изменено: `["content^2", "resource_title", "resource_type", "model_number"]`
- ✅ Изменено: индекс на `aeat_resources`
- ✅ Добавлено: resource_url, model_number в метаданные

## Результаты

### До фикса:
```
PDF search: 0 results ❌
Telegram search: 0 results ❌
```

### После фикса:
```
PDF search: 10 results ✅
Telegram search: 10 results ✅
Processing time: ~300ms ✅
```

## Тестирование

```bash
# Тест на сервере
curl -X POST http://63.180.170.54/search \
  -H "Content-Type: application/json" \
  -d '{
    "user_context": {"channel_type": "telegram", "channel_user_id": "test123"},
    "query_text": "IVA tipos",
    "channels": ["pdf", "telegram"]
  }'
```

**Результат:** 
- Status: 200 accepted
- Search: 10 PDF results found
- Webhook: Results sent successfully (200 OK)

## Структура индексов Elasticsearch

### pdf_documents (4,051 docs)
```json
{
  "document_id": "IVA_Value_Added_Tax",
  "chunk_id": "IVA_Value_Added_Tax_chunk_0",
  "chunk_index": 0,
  "content": "...",
  "document_title": "IVA - Value Added Tax",
  "document_type": "tax_law",
  "document_number": "37/1992",
  "categories": ["iva"],
  "tax_related": true,
  "indexed_at": "2025-10-04T19:50:34",
  "source": "tax_documents"
}
```

### telegram_threads (75,714 docs)
```json
{
  "thread_id": 21565,
  "group_name": "IT Autonomos Spain",
  "group_type": "it_autonomos",
  "message_count": 20,
  "content": "...",
  "first_message": "...",
  "last_message": "...",
  "topics": ["tax", "visa"],
  "keywords": ["автономо", "налог"],
  "quality_score": 5.0,
  "content_embedding": [...]
}
```

### calendar_deadlines (0 docs)
- Индекс существует, но пустой
- Нужно заполнить данными

### news_articles (0 docs)
- Индекс существует, но пустой
- Нужно заполнить данными

## Дополнительные улучшения

1. **Добавлено логирование**
   - Каждый метод поиска логирует количество результатов
   - Логируются ошибки с полным traceback

2. **Улучшена обработка ошибок**
   - `import traceback` и `traceback.print_exc()` в каждом except
   - Явное сообщение "Elasticsearch client not available"

3. **Оптимизация поиска**
   - Boosting на поле content (^2) для приоритета основного текста
   - Обрезка длинных результатов до 500 символов

## Файлы изменены

- `app/services/search_service.py` - все методы поиска
- `docs/webhook_api_documentation.md` - обновлена документация
- `docs/N8N_EXAMPLES.md` - обновлены примеры
- `.gitignore` - добавлен `.server_access`
- `.server_access` - SSH доступ к серверу (не коммитится)

## Деплой

```bash
# 1. Скопировать файл на сервер
scp -i ~/.ssh/key.pem app/services/search_service.py ubuntu@63.180.170.54:~/impuesto_bot/app/services/

# 2. Перезапустить контейнер
ssh -i ~/.ssh/key.pem ubuntu@63.180.170.54 "cd impuesto_bot && docker-compose restart app"

# 3. Проверить логи
ssh -i ~/.ssh/key.pem ubuntu@63.180.170.54 "docker logs impuesto-bot-api --tail 50"
```

## Следующие шаги

- [ ] Заполнить calendar_deadlines данными
- [ ] Заполнить news_articles данными
- [ ] Добавить гибридный semantic + keyword поиск
- [ ] Реализовать re-ranking результатов

---

*Fixed by NAIL - 2025-10-26 20:16 UTC*

