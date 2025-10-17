# TuExpertoFiscal API - Quick Start Guide

## Быстрый старт 🚀

Этот гайд поможет запустить API за 5 минут!

## Шаг 1: Установка зависимостей

```bash
# Активируй виртуальное окружение
source venv/bin/activate  # Linux/Mac
# или
.\venv\Scripts\activate  # Windows

# Установи зависимости
pip install -r requirements.txt
```

## Шаг 2: Настройка переменных окружения

Убедись, что у тебя есть файл `.env` с необходимыми ключами:

```bash
# Проверь файл .env
cat .env
```

Минимально необходимые переменные:
- `OPENAI_API_KEY` - для LLM и эмбеддингов
- `ELASTIC_CLOUD_ID` - для поиска
- `ELASTIC_API_KEY` - для поиска
- `SUPABASE_DB_URL` - для базы данных

## Шаг 3: Запуск сервера

### Вариант 1: Через main.py

```bash
python main.py
```

### Вариант 2: Через uvicorn

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Вариант 3: Продакшн режим

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Шаг 4: Проверка работоспособности

### Health Check

```bash
curl http://localhost:8000/health
```

Ожидаемый ответ:
```json
{
  "status": "healthy",
  "elasticsearch_connected": true,
  "supabase_connected": true,
  "llm_initialized": true,
  "timestamp": "2025-10-08T10:30:00Z"
}
```

### Тестовый запрос поиска

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "user_context": {
      "channel_type": "test",
      "channel_user_id": "test-user-123"
    },
    "query_text": "¿Qué es el IVA?",
    "top_k": 3,
    "generate_response": true
  }'
```

## Шаг 5: Просмотр документации

Открой в браузере:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Запуск тестов

### Все тесты

```bash
pytest
```

### С покрытием кода

```bash
pytest --cov=app --cov-report=html
```

### Только unit тесты

```bash
pytest tests/test_search_service.py
```

### Только webhook тесты

```bash
pytest tests/test_webhook.py
```

## Интеграция с N8N

### Шаг 1: Создай HTTP Request Node

В N8N создай **HTTP Request** ноду со следующими параметрами:

- **Method**: POST
- **URL**: `http://your-server:8000/search`
- **Body Content Type**: JSON

### Шаг 2: Настрой тело запроса

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

### Шаг 3: Обработай ответ

Используй данные из ответа:
- `{{$json.generated_response}}` - ответ LLM
- `{{$json.results}}` - массив найденных источников
- `{{$json.session_id}}` - сохрани для следующего запроса

## Примеры запросов

### Пример 1: Простой вопрос

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "user_context": {
      "channel_type": "telegram",
      "channel_user_id": "123456789"
    },
    "query_text": "¿Cuándo tengo que presentar el modelo 303?"
  }'
```

### Пример 2: С фильтрами по источникам

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "user_context": {
      "channel_type": "telegram",
      "channel_user_id": "123456789"
    },
    "query_text": "modelo 303 plazo",
    "filters": {
      "source_types": ["calendar", "aeat"],
      "tax_types": ["IVA"]
    },
    "top_k": 5
  }'
```

### Пример 3: Только источники (без LLM)

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "user_context": {
      "channel_type": "web",
      "channel_user_id": "web-user-456"
    },
    "query_text": "IVA autónomos",
    "top_k": 10,
    "generate_response": false
  }'
```

### Пример 4: Продолжение диалога

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "user_context": {
      "channel_type": "telegram",
      "channel_user_id": "123456789",
      "session_id": "660e8400-e29b-41d4-a716-446655440001"
    },
    "query_text": "¿Y para el modelo 111?"
  }'
```

## Мониторинг

### Проверка статуса

```bash
# Health check
curl http://localhost:8000/health

# Statistics
curl http://localhost:8000/stats
```

### Логи

Логи выводятся в stdout:

```bash
# Следить за логами
tail -f logs/api.log

# Или при запуске через uvicorn
uvicorn main:app --log-level info
```

## Отладка

### Проблема: Service not initialized

**Решение**: Проверь подключение к Elasticsearch и Supabase

```bash
# Проверь переменные окружения
env | grep ELASTIC
env | grep SUPABASE
```

### Проблема: Embedding generation fails

**Решение**: Проверь API ключ OpenAI

```bash
# Проверь ключ
env | grep OPENAI_API_KEY

# Тест подключения
python scripts/test_llm_providers.py
```

### Проблема: Database connection error

**Решение**: Проверь подключение к Supabase

```bash
# Тест подключения
python scripts/test_supabase_connection.py
```

## Деплой в продакшн

### Вариант 1: Systemd (Linux)

Создай файл `/etc/systemd/system/tuexpertofiscal-api.service`:

```ini
[Unit]
Description=TuExpertoFiscal API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/impuesto_bot
Environment="PATH=/path/to/impuesto_bot/venv/bin"
ExecStart=/path/to/impuesto_bot/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl start tuexpertofiscal-api
sudo systemctl enable tuexpertofiscal-api
```

### Вариант 2: Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t tuexpertofiscal-api .
docker run -p 8000:8000 --env-file .env tuexpertofiscal-api
```

### Вариант 3: Nginx + Gunicorn

```bash
# Установи gunicorn
pip install gunicorn

# Запусти
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

Nginx конфиг:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Полезные команды

```bash
# Запуск тестов с verbose
pytest -v

# Запуск тестов с coverage
pytest --cov=app --cov-report=term-missing

# Проверка линтером
flake8 app/

# Форматирование кода
black app/

# Проверка типов
mypy app/

# Запуск с hot-reload
uvicorn main:app --reload

# Запуск с конкретным хостом и портом
uvicorn main:app --host 0.0.0.0 --port 8080

# Генерация OpenAPI schema
python -c "from app.api.webhook import app; import json; print(json.dumps(app.openapi(), indent=2))" > openapi.json
```

## Troubleshooting

### Ошибка: ModuleNotFoundError

```bash
# Переустанови зависимости
pip install -r requirements.txt --force-reinstall
```

### Ошибка: Port already in use

```bash
# Найди процесс
lsof -i :8000

# Убей процесс
kill -9 <PID>
```

### Ошибка: Permission denied

```bash
# Дай права на выполнение
chmod +x main.py
```

## Поддержка

- 📚 **Полная документация**: `docs/webhook_api_documentation.md`
- 🔧 **API Docs**: http://localhost:8000/docs
- ❤️ **Health Check**: http://localhost:8000/health

---

**Готово!** Теперь у тебя запущен мощный AI-ассистент для налоговых вопросов! 🔥

