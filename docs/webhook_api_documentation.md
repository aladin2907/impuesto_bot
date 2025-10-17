# TuExpertoFiscal - Webhook API Documentation

## Обзор

Webhook API для интеграции с N8N. Предоставляет интеллектуальный поиск по налоговой базе знаний с использованием гибридного поиска (Elasticsearch) и генерацией ответов через LLM.

## Базовая информация

- **Base URL**: `http://your-server:8000`
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

### 2. Search (Main Endpoint)

Основной эндпоинт для поиска - принимает запросы от N8N.

**Endpoint**: `POST /search`

**Request Body**:

```json
{
  "user_context": {
    "channel_type": "telegram",
    "channel_user_id": "123456789",
    "user_metadata": {
      "username": "john_doe",
      "first_name": "John"
    },
    "session_id": "optional-existing-session-uuid"
  },
  "query_text": "¿Cuándo tengo que presentar el modelo 303?",
  "filters": {
    "source_types": ["calendar", "aeat", "pdf", "news", "telegram"],
    "date_from": "2025-01-01T00:00:00Z",
    "date_to": "2025-12-31T23:59:59Z",
    "tax_types": ["IVA", "IRPF", "Sociedades"],
    "regions": ["national", "Cataluña", "Madrid"],
    "only_tax_related": true,
    "minimum_quality_score": 2.0
  },
  "top_k": 5,
  "generate_response": true
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
| `filters` | object | Нет | Фильтры поиска |
| `filters.source_types` | array | Нет | Типы источников (calendar, pdf, news, telegram, aeat, regional, all) |
| `filters.date_from` | datetime | Нет | Фильтр по дате от |
| `filters.date_to` | datetime | Нет | Фильтр по дате до |
| `filters.tax_types` | array | Нет | Типы налогов (IVA, IRPF, Sociedades, etc.) |
| `filters.regions` | array | Нет | Регионы (national, Cataluña, Madrid, etc.) |
| `filters.only_tax_related` | boolean | Нет | Только налоговый контент (default: true) |
| `filters.minimum_quality_score` | float | Нет | Мин. оценка качества 0.0-5.0 (default: 2.0) |
| `top_k` | integer | Нет | Количество результатов (1-20, default: 5) |
| `generate_response` | boolean | Нет | Генерировать LLM ответ (default: true) |

**Response**:

```json
{
  "success": true,
  "query_text": "¿Cuándo tengo que presentar el modelo 303?",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "660e8400-e29b-41d4-a716-446655440001",
  "results": [
    {
      "text": "El modelo 303 debe presentarse trimestralmente...",
      "metadata": {
        "source_type": "calendar",
        "tax_type": "IVA",
        "deadline_date": "2025-04-20"
      },
      "score": 0.95,
      "source_type": "calendar"
    }
  ],
  "generated_response": "El modelo 303 de IVA debe presentarse trimestralmente en los siguientes plazos...",
  "subscription_status": "free",
  "processing_time_ms": 1250,
  "error_message": null
}
```

**Response Fields**:

| Поле | Тип | Описание |
|------|-----|----------|
| `success` | boolean | Успешность запроса |
| `query_text` | string | Исходный текст запроса |
| `user_id` | string | UUID пользователя в нашей системе |
| `session_id` | string | UUID сессии диалога |
| `results` | array | Массив результатов поиска |
| `results[].text` | string | Текст найденного фрагмента |
| `results[].metadata` | object | Метаданные источника |
| `results[].score` | float | Оценка релевантности |
| `results[].source_type` | string | Тип источника |
| `generated_response` | string | Сгенерированный LLM ответ (если запрошено) |
| `subscription_status` | string | Статус подписки (free, premium) |
| `processing_time_ms` | integer | Время обработки в миллисекундах |
| `error_message` | string | Сообщение об ошибке (если success=false) |

**Status Codes**:
- `200`: Успешный запрос (даже если success=false в теле)
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

**HTTP Request Node**:
```json
{
  "method": "POST",
  "url": "http://your-server:8000/search",
  "body": {
    "user_context": {
      "channel_type": "telegram",
      "channel_user_id": "{{$json.message.from.id}}"
    },
    "query_text": "{{$json.message.text}}"
  }
}
```

### Пример 2: Запрос с фильтрами

**HTTP Request Node**:
```json
{
  "method": "POST",
  "url": "http://your-server:8000/search",
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
    "filters": {
      "source_types": ["calendar", "aeat"],
      "tax_types": ["IVA"],
      "only_tax_related": true
    },
    "top_k": 5,
    "generate_response": true
  }
}
```

### Пример 3: Продолжение диалога

**HTTP Request Node**:
```json
{
  "method": "POST",
  "url": "http://your-server:8000/search",
  "body": {
    "user_context": {
      "channel_type": "telegram",
      "channel_user_id": "{{$json.message.from.id}}",
      "session_id": "{{$json.previous_session_id}}"
    },
    "query_text": "{{$json.message.text}}"
  }
}
```

---

## Типы источников данных

| source_type | Описание |
|-------------|----------|
| `telegram` | Треды из Telegram групп |
| `pdf` | PDF документы (законы, регламенты) |
| `calendar` | Налоговый календарь (дедлайны) |
| `news` | Новостные статьи |
| `aeat` | Ресурсы AEAT (формы, инструкции) |
| `regional` | Региональные источники |
| `all` | Все источники |

---

## Типы налогов (tax_types)

- `IVA` - НДС
- `IRPF` - Налог на доходы физлиц
- `Sociedades` - Налог на прибыль
- `Patrimonio` - Налог на имущество
- `Sucesiones` - Налог на наследство
- `Donaciones` - Налог на дарение

---

## Регионы (regions)

- `national` - Национальный уровень
- `Cataluña` - Каталония
- `Madrid` - Мадрид
- `Andalucía` - Андалусия
- `Valencia` - Валенсия
- ... и другие автономные сообщества

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

### 1. Управление сессиями

Для контекстных диалогов сохраняйте `session_id` из ответа и передавайте его в следующих запросах:

```javascript
// В N8N Flow
const previousSession = $node["Search"].json.session_id;
```

### 2. Использование фильтров

Фильтры помогают сузить поиск и получить более релевантные результаты:

- Для вопросов о дедлайнах: `source_types: ["calendar"]`
- Для законодательства: `source_types: ["pdf", "aeat"]`
- Для практических советов: `source_types: ["telegram", "news"]`

### 3. Оптимизация производительности

- Используйте `top_k` от 3 до 7 для баланса между качеством и скоростью
- Отключайте `generate_response: false` если нужны только источники
- Кешируйте частые запросы в N8N

### 4. Мониторинг

Регулярно проверяйте `/health` для мониторинга состояния:

```javascript
// N8N Cron Node - каждые 5 минут
GET http://your-server:8000/health
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

### v1.0.0 (2025-10-08)
- ✅ Основной search endpoint
- ✅ Health check endpoint
- ✅ Гибридный поиск (semantic + keyword)
- ✅ LLM генерация ответов
- ✅ Фильтрация по источникам, датам, типам налогов
- ✅ Управление сессиями и пользователями
- ✅ Swagger документация

