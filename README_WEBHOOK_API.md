# TuExpertoFiscal - Webhook API для N8N 🚀

## Описание

Мощный FastAPI вебхук для интеграции с N8N. Предоставляет интеллектуальный поиск по налоговой базе знаний с использованием:
- 🔍 **Гибридный поиск** (semantic + keyword) через Elasticsearch
- 🤖 **LLM генерация ответов** через OpenAI/Gemini/Claude
- 💾 **Управление пользователями и сессиями** через Supabase
- 🎯 **Мультисурс поиск** (Telegram, PDF, новости, календари, AEAT)

## Архитектура

```
N8N → Webhook API → Search Service → {Elasticsearch, Supabase, LLM} → Response
```

### Компоненты:

1. **app/models/search.py** - Pydantic модели для запросов/ответов
2. **app/services/search_service.py** - Унифицированный поисковый сервис
3. **app/api/webhook.py** - FastAPI endpoints
4. **main.py** - Точка входа приложения

## Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка .env

Убедись, что настроены все переменные окружения:

```bash
# Minimum required
OPENAI_API_KEY=your_key
ELASTIC_CLOUD_ID=your_id
ELASTIC_API_KEY=your_key
SUPABASE_DB_URL=postgresql://...
```

### 3. Запуск сервера

```bash
python main.py
# или
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Проверка

```bash
curl http://localhost:8000/health
```

## API Endpoints

### 🏥 GET /health

Проверка здоровья всех сервисов.

**Response:**
```json
{
  "status": "healthy",
  "elasticsearch_connected": true,
  "supabase_connected": true,
  "llm_initialized": true,
  "timestamp": "2025-10-08T10:30:00Z"
}
```

### 🔍 POST /search

Основной поисковый эндпоинт.

**Request:**
```json
{
  "user_context": {
    "channel_type": "telegram",
    "channel_user_id": "123456789",
    "user_metadata": {"username": "john_doe"},
    "session_id": "optional-existing-session-uuid"
  },
  "query_text": "¿Cuándo tengo que presentar el modelo 303?",
  "filters": {
    "source_types": ["calendar", "aeat"],
    "tax_types": ["IVA"],
    "date_from": "2025-01-01T00:00:00Z",
    "only_tax_related": true
  },
  "top_k": 5,
  "generate_response": true
}
```

**Response:**
```json
{
  "success": true,
  "query_text": "¿Cuándo tengo que presentar el modelo 303?",
  "user_id": "uuid-here",
  "session_id": "uuid-here",
  "results": [
    {
      "text": "El modelo 303 debe presentarse...",
      "metadata": {"source_type": "calendar", "tax_type": "IVA"},
      "score": 0.95,
      "source_type": "calendar"
    }
  ],
  "generated_response": "El modelo 303 de IVA...",
  "subscription_status": "free",
  "processing_time_ms": 1250
}
```

### 📊 GET /stats

Статистика сервиса.

## Параметры поиска

### Source Types (Типы источников)

- `telegram` - Треды из Telegram групп
- `pdf` - PDF документы (законы, регламенты)
- `calendar` - Налоговый календарь
- `news` - Новостные статьи
- `aeat` - Ресурсы AEAT
- `regional` - Региональные источники
- `all` - Все источники

### Tax Types (Типы налогов)

- `IVA` - НДС
- `IRPF` - Налог на доходы физлиц
- `Sociedades` - Налог на прибыль
- `Patrimonio` - Налог на имущество
- `Sucesiones` - Налог на наследство
- `Donaciones` - Налог на дарение

### Filters (Фильтры)

| Фильтр | Тип | Описание |
|--------|-----|----------|
| `source_types` | array | Фильтр по типам источников |
| `date_from/date_to` | datetime | Временной диапазон |
| `tax_types` | array | Фильтр по типам налогов |
| `regions` | array | Фильтр по регионам |
| `only_tax_related` | bool | Только налоговый контент |
| `minimum_quality_score` | float | Мин. качество (0.0-5.0) |

## Интеграция с N8N

### Базовая настройка

1. **Создай HTTP Request Node**
2. **Настрой параметры:**
   - Method: `POST`
   - URL: `http://your-server:8000/search`
   - Body Content Type: `JSON`

3. **Тело запроса:**
```json
{
  "user_context": {
    "channel_type": "telegram",
    "channel_user_id": "{{$json.message.from.id}}"
  },
  "query_text": "{{$json.message.text}}",
  "top_k": 5,
  "generate_response": true
}
```

### Продвинутые сценарии

#### 1. Контекстный диалог

Сохраняй `session_id` и передавай в следующих запросах:

```javascript
// В N8N Function Node
const sessionId = $node["Search"].json.session_id;

return {
  user_context: {
    channel_type: "telegram",
    channel_user_id: $json.message.from.id,
    session_id: sessionId  // Сохраненный из предыдущего запроса
  },
  query_text: $json.message.text
};
```

#### 2. Умная фильтрация

Анализируй вопрос и применяй фильтры:

```javascript
// В N8N Function Node
const query = $json.message.text.toLowerCase();

let filters = {};

// Если вопрос о дедлайнах
if (query.includes('cuando') || query.includes('plazo')) {
  filters.source_types = ['calendar'];
}

// Если вопрос о законах
if (query.includes('ley') || query.includes('normativa')) {
  filters.source_types = ['pdf', 'aeat'];
}

// Если упоминается IVA
if (query.includes('iva') || query.includes('303')) {
  filters.tax_types = ['IVA'];
}

return {
  user_context: {...},
  query_text: $json.message.text,
  filters: filters
};
```

#### 3. Обработка ответа

```javascript
// В N8N Function Node
const response = $json;

if (response.success) {
  // Отправь LLM ответ пользователю
  const message = response.generated_response;
  
  // Сохрани session_id для следующего раза
  const sessionId = response.session_id;
  
  // Проверь подписку
  if (response.subscription_status === 'free') {
    // Возможно, добавь сообщение о премиуме
  }
  
  return {
    message: message,
    sessionId: sessionId
  };
} else {
  return {
    message: "Lo siento, ocurrió un error: " + response.error_message
  };
}
```

## Тестирование

### Unit тесты

```bash
# Все тесты
pytest

# С coverage
pytest --cov=app --cov-report=html

# Только search service
pytest tests/test_search_service.py -v

# Только webhook
pytest tests/test_webhook.py -v
```

### Integration тесты

```bash
# Запусти сервер
python main.py

# В другом терминале
python scripts/test_webhook_api.py
```

### Ручное тестирование

```bash
# Health check
curl http://localhost:8000/health

# Простой поиск
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "user_context": {
      "channel_type": "test",
      "channel_user_id": "test-123"
    },
    "query_text": "¿Qué es el IVA?"
  }'
```

## Мониторинг и логи

### Логирование

Все запросы логируются:

```
2025-10-08 10:30:00 - INFO - Search request from telegram:123456789
2025-10-08 10:30:00 - INFO - Query: ¿Cuándo tengo que presentar el modelo 303?
2025-10-08 10:30:01 - INFO - Search successful: 5 results, 1250ms
```

### Metrics

API автоматически трекает:
- Processing time (в каждом ответе)
- Success/failure rate (в логах)
- User sessions (в Supabase)

### Health monitoring

Настрой в N8N регулярную проверку:

```
Cron Trigger (каждые 5 минут)
  ↓
HTTP Request: GET /health
  ↓
IF status != "healthy"
  ↓
Send Alert (Telegram/Email)
```

## Production Deployment

### Systemd Service

```ini
[Unit]
Description=TuExpertoFiscal API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/impuesto_bot
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

### Docker

```bash
docker build -t tuexpertofiscal-api .
docker run -p 8000:8000 --env-file .env tuexpertofiscal-api
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name api.tuexpertofiscal.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## Безопасность

### В продакшн:

1. ✅ Добавь HTTPS (Let's Encrypt)
2. ✅ Настрой CORS для конкретных origins
3. ✅ Добавь rate limiting
4. ✅ Используй API keys для аутентификации
5. ✅ Не логируй чувствительные данные
6. ✅ Валидируй все входные данные (уже есть через Pydantic)

## Документация

- 📖 **API Docs**: http://localhost:8000/docs (Swagger UI)
- 📘 **ReDoc**: http://localhost:8000/redoc
- 📚 **Full Docs**: `docs/webhook_api_documentation.md`
- 🚀 **Quick Start**: `docs/API_QUICKSTART.md`

## Troubleshooting

### Проблема: Service not initialized

**Решение**: Проверь подключения к Elasticsearch и Supabase

```bash
curl http://localhost:8000/health
```

### Проблема: Slow response times

**Решение**: 
- Увеличь кеширование
- Уменьши `top_k`
- Отключи `generate_response` если не нужно

### Проблема: Database errors

**Решение**: Проверь Supabase connection:

```bash
python scripts/test_supabase_connection.py
```

## Roadmap

- [ ] Rate limiting
- [ ] API key authentication
- [ ] Response caching
- [ ] Async bulk search
- [ ] Webhooks для уведомлений
- [ ] GraphQL endpoint
- [ ] Streaming responses

## Contributing

Следуй TDD практике:
1. Напиши тесты
2. Реализуй функциональность
3. Проверь линтером
4. Запусти все тесты

## License

Proprietary - TuExpertoFiscal NAIL Project

---

**Сделано с 🔥 по TDD практике!** YO

