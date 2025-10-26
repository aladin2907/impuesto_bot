# TuExpertoFiscal - Webhook API Documentation

## Обзор

Webhook API для интеграции с N8N. Предоставляет интеллектуальный поиск по налоговой базе знаний с использованием гибридного поиска (Elasticsearch) и генерацией ответов через LLM.

## 🚀 Быстрый старт

### Как это работает:

```
N8N → POST /search → 200 OK (сразу)
         ↓
    Background Task (поиск в Elasticsearch)
         ↓
    POST webhook_url → N8N (результаты)
```

### Минимальный запрос:

```bash
curl -X POST http://63.180.170.54/search \
  -H "Content-Type: application/json" \
  -d '{
    "user_context": {
      "channel_type": "telegram",
      "channel_user_id": "123456789"
    },
    "query_text": "Какой размер НДС в Испании?",
    "channels": ["pdf", "aeat"]
  }'
```

**Ответ (сразу)**: `{"status": "accepted", ...}`  
**Результаты** придут на webhook: `https://n8n.mafiavlc.org/webhook/59c06e61-a477-42df-8959-20f056f33189`

---

## Базовая информация

- **Production URL**: `http://63.180.170.54/search`
- **N8N Webhook**: `https://n8n.mafiavlc.org/webhook/59c06e61-a477-42df-8959-20f056f33189`
- **Формат**: JSON
- **Документация**: `/docs` (Swagger UI)
- **Health Check**: `/health`

## Эндпоинты

### 1. Health Check

Проверка статуса всех сервисов.

**Endpoint**: `GET /health`

**Response**:
```json
{
  "status": "healthy",
  "elasticsearch_connected": true,
  "supabase_connected": true,
  "llm_initialized": true,
  "timestamp": "2025-10-08T10:30:00Z"
}
```

**Status Codes**:
- `200`: Все сервисы работают
- `503`: Один или более сервисов недоступны

---

### 2. Search (Main Endpoint) - АСИНХРОННЫЙ

⚠️ **ВАЖНО**: Этот эндпоинт работает АСИНХРОННО!
- Сервер немедленно возвращает `200 OK` (запрос принят)
- Поиск выполняется в фоновом режиме
- Результаты отправляются POST-запросом на `webhook_url` (N8N webhook)

**Endpoint**: `POST /search`

**Request Body**:

```json
{
  "user_context": {
    "channel_type": "telegram",
    "channel_user_id": "7147294726",
    "user_metadata": {
      "username": "VadymNahornyi",
      "first_name": "Vadim"
    },
    "session_id": "optional-existing-session-uuid"
  },
  "query_text": "Какой размер НДС в Испании?",
  "channels": ["pdf", "aeat", "telegram", "calendar", "news"],
  "top_k": 5,
  "webhook_url": "https://n8n.mafiavlc.org/webhook/59c06e61-a477-42df-8959-20f056f33189"
}
```

**Request Parameters**:

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `user_context` | object | Да | Контекст пользователя |
| `user_context.channel_type` | string | Да | Тип канала (telegram, whatsapp, web, etc.) |
| `user_context.channel_user_id` | string | Да | ID пользователя в канале |
| `user_context.user_metadata` | object | Нет | Доп. метаданные (username, first_name, etc.) |
| `user_context.session_id` | string | Нет | ID существующей сессии (для продолжения диалога) |
| `query_text` | string | Да | Текст запроса (1-1000 символов) |
| `channels` | array | Да | Список каналов для поиска: ["telegram", "pdf", "calendar", "news", "aeat"] |
| `top_k` | integer | Нет | Количество результатов (1-20, default: 5) |
| `webhook_url` | string | Нет | URL N8N webhook для отправки результатов (default: https://n8n.mafiavlc.org/webhook/59c06e61-a477-42df-8959-20f056f33189) |

**Немедленный Response (200 OK)**:

```json
{
  "status": "accepted",
  "message": "Search request accepted and processing in background",
  "query": "Какой размер НДС в Испании?",
  "channels": ["pdf", "aeat"]
}
```

**Callback на webhook_url (результаты поиска)**:

После завершения поиска сервер отправляет POST-запрос на `webhook_url`:

```json
{
  "success": true,
  "query_text": "Какой размер НДС в Испании?",
  "user_id": "mock_user_7147294726",
  "session_id": "mock_session_mock_user_7147294726_1761507882",
  "telegram_results": [
    {
      "text": "В IT Autonomos обсуждали ставки НДС...",
      "metadata": {
        "group_name": "IT Autonomos Spain",
        "topics": ["IVA", "taxes"]
      },
      "score": 0.95,
      "source_type": "telegram"
    }
  ],
  "pdf_results": [
    {
      "text": "Согласно Ley 37/1992, стандартная ставка НДС...",
      "metadata": {
        "filename": "Ley_37_1992.pdf",
        "title": "Ley del IVA"
      },
      "score": 0.92,
      "source_type": "pdf"
    }
  ],
  "calendar_results": [],
  "news_results": [],
  "subscription_status": "free",
  "error_message": null,
  "processing_time_ms": 515
}
```

**Callback Response Fields**:

| Поле | Тип | Описание |
|------|-----|----------|
| `success` | boolean | Успешность поиска |
| `query_text` | string | Исходный текст запроса |
| `user_id` | string | ID пользователя в системе |
| `session_id` | string | ID сессии диалога |
| `telegram_results` | array | Результаты из Telegram групп |
| `pdf_results` | array | Результаты из PDF документов |
| `calendar_results` | array | Результаты из налогового календаря |
| `news_results` | array | Результаты из новостей |
| `subscription_status` | string | Статус подписки (free, premium) |
| `error_message` | string\|null | Сообщение об ошибке (если success=false) |
| `processing_time_ms` | integer | Время обработки в миллисекундах |

**Формат результатов по каждому каналу**:

```typescript
{
  "text": string,          // Текст найденного фрагмента
  "metadata": object,      // Метаданные (зависят от источника)
  "score": float,          // Оценка релевантности (0.0-1.0)
  "source_type": string    // Тип источника
}
```

**Status Codes**:
- `200`: Запрос принят (обработка началась)
- `422`: Ошибка валидации входных данных
- `500`: Внутренняя ошибка сервера

---

### 3. Statistics

Получение статистики сервиса (для мониторинга).

**Endpoint**: `GET /stats`

**Response**:
```json
{
  "status": "operational",
  "services": {
    "elasticsearch_connected": true,
    "supabase_connected": true,
    "llm_initialized": true,
    "search_service_initialized": true
  },
  "timestamp": "2025-10-08T10:30:00Z"
}
```

---

## Примеры использования в N8N

### Пример 1: Простой запрос

**HTTP Request Node** (отправка запроса):
```json
{
  "method": "POST",
  "url": "http://63.180.170.54/search",
  "body": {
    "user_context": {
      "channel_type": "telegram",
      "channel_user_id": "{{$json.message.from.id}}",
      "user_metadata": {
        "username": "{{$json.message.from.username}}",
        "first_name": "{{$json.message.from.first_name}}"
      }
    },
    "query_text": "{{$json.message.text}}",
    "channels": ["telegram", "pdf", "calendar"],
    "top_k": 5
  }
}
```

**⚠️ Важно**: Нужен **отдельный Webhook Trigger** для приема результатов!

**Webhook Trigger** (прием результатов):
```
URL: https://n8n.mafiavlc.org/webhook/59c06e61-a477-42df-8959-20f056f33189
Method: POST
```

Данные придут в формате:
```json
{
  "success": true,
  "query_text": "...",
  "telegram_results": [...],
  "pdf_results": [...],
  "calendar_results": [...],
  "news_results": [...]
}
```

### Пример 2: Поиск в конкретных каналах

**HTTP Request Node**:
```json
{
  "method": "POST",
  "url": "http://63.180.170.54/search",
  "body": {
    "user_context": {
      "channel_type": "telegram",
      "channel_user_id": "{{$json.message.from.id}}",
      "user_metadata": {
        "username": "{{$json.message.from.username}}",
        "first_name": "{{$json.message.from.first_name}}"
      }
    },
    "query_text": "{{$json.message.text}}",
    "channels": ["pdf", "aeat"],  // Только PDF и AEAT
    "top_k": 5,
    "webhook_url": "https://n8n.mafiavlc.org/webhook/YOUR-WEBHOOK-ID"
  }
}
```

### Пример 3: Продолжение диалога

**HTTP Request Node**:
```json
{
  "method": "POST",
  "url": "http://63.180.170.54/search",
  "body": {
    "user_context": {
      "channel_type": "telegram",
      "channel_user_id": "{{$json.message.from.id}}",
      "session_id": "{{$json.previous_session_id}}"  // ID предыдущей сессии
    },
    "query_text": "{{$json.message.text}}",
    "channels": ["telegram", "pdf"],
    "top_k": 5
  }
}
```

### Пример 4: Полный N8N Workflow

```
┌─────────────────────┐
│ Telegram Trigger    │ ← Входящее сообщение от пользователя
└──────────┬──────────┘
           │
           ↓
┌─────────────────────┐
│ HTTP Request        │ ← POST /search (возвращает 200 accepted)
│ (POST /search)      │
└──────────┬──────────┘
           │
           ↓
┌─────────────────────┐
│ Telegram: "Ищу..."  │ ← Уведомление пользователю о начале поиска
└─────────────────────┘

(параллельно)

┌─────────────────────┐
│ Webhook Trigger     │ ← Прием результатов с сервера
│ (отдельный workflow)│
└──────────┬──────────┘
           │
           ↓
┌─────────────────────┐
│ Function: Format    │ ← Форматирование результатов
└──────────┬──────────┘
           │
           ↓
┌─────────────────────┐
│ Telegram: Send      │ ← Отправка ответа пользователю
└─────────────────────┘
```

---

## Доступные каналы (channels)

В параметре `channels` можно указать список источников для поиска:

| Канал | Описание | Индекс Elasticsearch |
|-------|----------|---------------------|
| `telegram` | Треды из Telegram групп (IT Autonomos, Digital Nomads) | `telegram_threads` |
| `pdf` | PDF документы (Ley IRPF, IVA, налоговый кодекс) | `pdf_documents` |
| `calendar` | Налоговый календарь AEAT (дедлайны, сроки) | `calendar_deadlines` |
| `news` | Новостные статьи (Cinco Días, Expansión) | `news_articles` |
| `aeat` | Ресурсы AEAT (формы, инструкции, FAQ) | `aeat` |

**Пример**: `"channels": ["pdf", "aeat", "telegram"]`

---

## Обработка ошибок

### Ошибки валидации (422)

```json
{
  "detail": [
    {
      "loc": ["body", "query_text"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Ошибки сервиса (200 с success=false)

```json
{
  "success": false,
  "query_text": "test query",
  "error_message": "Failed to generate embedding",
  "processing_time_ms": 150
}
```

### Внутренние ошибки (500)

```json
{
  "success": false,
  "error_message": "Internal server error",
  "detail": "Connection timeout"
}
```

---

## Рекомендации по интеграции

### 1. Асинхронная обработка - ВАЖНО! ⚠️

Эндпоинт `/search` работает АСИНХРОННО. Вам нужны **два отдельных workflow в N8N**:

**Workflow 1** - Отправка запроса:
```
Telegram Trigger → HTTP POST /search → Telegram "Ищу информацию..."
```

**Workflow 2** - Прием результатов:
```
Webhook Trigger → Function (форматирование) → Telegram (отправка ответа)
```

### 2. Управление сессиями

Для контекстных диалогов сохраняйте `session_id` из callback и передавайте его в следующих запросах:

```javascript
// В N8N Webhook Trigger (прием результатов)
const sessionId = $json.body.session_id;

// Сохраняем в Redis/Memory для следующего запроса
return {
  key: `session:${$json.body.user_id}`,
  value: sessionId
};
```

### 3. Выбор каналов для поиска

Правильно выбирайте каналы в зависимости от типа вопроса:

- **Дедлайны и сроки**: `["calendar", "aeat"]`
- **Законодательство**: `["pdf", "aeat"]`
- **Практические советы**: `["telegram", "news"]`
- **Универсальный поиск**: `["telegram", "pdf", "calendar", "news", "aeat"]`

### 4. Оптимизация производительности

- Используйте `top_k` от 3 до 7 для баланса между качеством и скоростью
- Не указывайте лишние каналы - это замедлит поиск
- Для quick FAQ используйте меньше каналов

### 5. Мониторинг

Регулярно проверяйте `/health` для мониторинга состояния:

```javascript
// N8N Cron Node - каждые 5 минут
GET http://63.180.170.54/health
```

### 6. Обработка пустых результатов

Всегда проверяйте результаты в callback:

```javascript
const { telegram_results, pdf_results, calendar_results, news_results } = $json.body;
const totalResults = 
  telegram_results.length + 
  pdf_results.length + 
  calendar_results.length + 
  news_results.length;

if (totalResults === 0) {
  return {
    message: "Lo siento, no encontré información relevante. ¿Puedes reformular tu pregunta?"
  };
}
```

---

## Безопасность

### В продакшене:

1. **CORS**: Настройте конкретные origins вместо `*`
2. **Rate Limiting**: Добавьте ограничение запросов
3. **Authentication**: Добавьте API ключи или JWT
4. **HTTPS**: Используйте только HTTPS
5. **Logging**: Не логируйте чувствительные данные

### Рекомендуемые заголовки:

```
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

---

## Поддержка

- **Документация**: http://your-server:8000/docs
- **ReDoc**: http://your-server:8000/redoc
- **Health**: http://your-server:8000/health

---

## Changelog

### v1.3.0 (2025-10-26) - MULTILINGUAL + CALENDAR
- 🌍 **NEW**: Поддержка 4 языков (ES, RU, UK, EN)
- ✅ Query translation для всех индексов
- ✅ Украинский: пдв→IVA, податок→impuesto, декларація→declaración
- ✅ Расширенный словарь RU/EN терминов
- 📅 **NEW**: Tax Calendar интеграция
- ✅ 28 deadlines проиндексированы (2025 + 2026)
- ✅ Calendar search с multilingual support
- 📰 **NEW**: AEAT Petete scraper (ready to use)
- 📖 Документация: [MULTILINGUAL_SEARCH.md](./MULTILINGUAL_SEARCH.md)

### v1.2.0 (2025-10-26) - HYBRID SEARCH
- 🚀 **NEW**: Гибридный поиск (kNN + BM25) для Telegram
- ✅ Semantic search через OpenAI embeddings (1536 dim)
- ✅ Комбинирование kNN (semantic) + multi_match (keyword)
- ✅ Scores выше (20-25 vs 9-10)
- ✅ Автоматический fallback на keyword-only
- ⚠️ Требует OpenAI API key для embeddings
- 📖 Документация: [HYBRID_SEARCH.md](./HYBRID_SEARCH.md)

### v1.1.0 (2025-10-26) - DOCUMENTATION FIX
- 🔥 **ИСПРАВЛЕНО**: Документация приведена в соответствие с реальной реализацией
- ✅ Асинхронная обработка `/search` с callback на N8N webhook
- ✅ Параметр `channels` вместо `filters.source_types`
- ✅ Разделенные результаты по каналам (telegram_results, pdf_results, etc.)
- ✅ Реальные URL: `http://63.180.170.54/search`
- ✅ Реальный N8N webhook: `https://n8n.mafiavlc.org/webhook/59c06e61-a477-42df-8959-20f056f33189`
- ✅ Обновлены примеры N8N и curl
- ✅ Добавлены рекомендации по асинхронной обработке

### v1.0.0 (2025-10-08)
- ✅ Основной search endpoint
- ✅ Health check endpoint  
- ✅ Keyword search (BM25)
- ✅ Управление сессиями и пользователями
- ✅ Swagger документация

