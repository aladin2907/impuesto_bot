# N8N Integration Examples для TuExpertoFiscal API

## Обзор

Этот документ содержит готовые примеры интеграции с N8N для разных сценариев использования.

## Базовая конфигурация N8N

### HTTP Request Node - Базовые настройки

```
Node Type: HTTP Request
Method: POST
URL: http://your-server:8000/search
Authentication: None (или Bearer Token если настроена)
Response Format: JSON
```

## Сценарий 1: Telegram Bot с простыми ответами

### Workflow структура:
```
Telegram Trigger → Function (Prepare Request) → HTTP Request (Search) → Function (Format Response) → Telegram Send Message
```

### Function Node: Prepare Request

```javascript
// Получаем сообщение от пользователя
const message = $json.message;

// Формируем запрос к API
return {
  user_context: {
    channel_type: "telegram",
    channel_user_id: String(message.from.id),
    user_metadata: {
      username: message.from.username || "",
      first_name: message.from.first_name || "",
      last_name: message.from.last_name || ""
    }
  },
  query_text: message.text,
  top_k: 5,
  generate_response: true
};
```

### HTTP Request Node: Search API

```json
{
  "method": "POST",
  "url": "http://your-server:8000/search",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": "={{$json}}"
}
```

### Function Node: Format Response

```javascript
const response = $json;

if (response.success) {
  return {
    chat_id: $node["Telegram Trigger"].json.message.chat.id,
    text: response.generated_response,
    parse_mode: "Markdown"
  };
} else {
  return {
    chat_id: $node["Telegram Trigger"].json.message.chat.id,
    text: "❌ Lo siento, no pude procesar tu pregunta. Error: " + response.error_message,
    parse_mode: "Markdown"
  };
}
```

---

## Сценарий 2: Контекстный диалог с сохранением сессии

### Workflow структура:
```
Telegram Trigger → Redis Get Session → Function (Prepare) → HTTP Request → Function (Save Session) → Redis Set → Telegram Reply
```

### Function Node: Prepare Request with Session

```javascript
const message = $json.message;
const userId = String(message.from.id);

// Получаем существующую сессию из Redis (если есть)
const existingSession = $node["Redis Get Session"].json?.session_id;

return {
  user_context: {
    channel_type: "telegram",
    channel_user_id: userId,
    user_metadata: {
      username: message.from.username || "",
      first_name: message.from.first_name || ""
    },
    session_id: existingSession || undefined
  },
  query_text: message.text,
  top_k: 5,
  generate_response: true
};
```

### Function Node: Save Session to Redis

```javascript
const response = $json;
const userId = $node["Telegram Trigger"].json.message.from.id;

if (response.success && response.session_id) {
  return {
    key: `session:${userId}`,
    value: JSON.stringify({
      session_id: response.session_id,
      last_updated: new Date().toISOString()
    }),
    ttl: 3600  // 1 час
  };
}

return null;
```

---

## Сценарий 3: Умная маршрутизация по типу вопроса

### Function Node: Smart Query Router

```javascript
const message = $json.message;
const query = message.text.toLowerCase();

// Базовый запрос
let request = {
  user_context: {
    channel_type: "telegram",
    channel_user_id: String(message.from.id)
  },
  query_text: message.text,
  top_k: 5,
  generate_response: true,
  filters: {}
};

// Определяем тип вопроса и применяем фильтры

// 1. Вопросы о дедлайнах и календаре
if (query.match(/cuando|plazo|fecha|deadline|calendario/)) {
  request.filters.source_types = ["calendar", "aeat"];
  request.filters.only_tax_related = true;
}

// 2. Вопросы о законодательстве
else if (query.match(/ley|normativa|regulacion|articulo|codigo/)) {
  request.filters.source_types = ["pdf", "aeat"];
  request.top_k = 3;  // Меньше результатов для законов
}

// 3. Практические вопросы (Telegram треды)
else if (query.match(/como|experiencia|alguien|quien|consejo/)) {
  request.filters.source_types = ["telegram", "news"];
  request.filters.minimum_quality_score = 3.0;
}

// 4. Новости и изменения
else if (query.match(/nuevo|cambio|actualizacion|noticia/)) {
  request.filters.source_types = ["news"];
  request.filters.date_from = new Date(Date.now() - 90*24*60*60*1000).toISOString(); // Последние 90 дней
}

// Определяем тип налога
if (query.match(/\biva\b|modelo 303|modelo 390/)) {
  request.filters.tax_types = ["IVA"];
}
else if (query.match(/irpf|renta|modelo 100/)) {
  request.filters.tax_types = ["IRPF"];
}
else if (query.match(/sociedades|modelo 200/)) {
  request.filters.tax_types = ["Sociedades"];
}

return request;
```

---

## Сценарий 4: Мультиисточниковый поиск с агрегацией

### Что делает
Новый эндпоинт `/n8n/search` позволяет передать список источников (`calendar`, `news`, `pdf`, `telegram`, `aeat`, `regional`) и получить раздельные результаты по каждому, а также сводный список без дубликатов. Дополнительно можно указать `callback_url`, и API отправит результаты обратно в N8N.

### Workflow структура
```
Cron / Trigger → Function (Prepare Multi Source Request) → HTTP Request (POST /n8n/search) → (опционально) ожидание callback → дальнейшие узлы
```

### Function Node: Prepare Request
```javascript
// Выбираем источники на основе логики
const sources = ["calendar", "news", "pdf"]; // пример

return {
  query_text: $json.query || "modelo 303",
  sources,
  top_k_per_source: 2,
  aggregate_results: true,
  request_id: $json.requestId || `n8n-${Date.now()}`,
  metadata: {
    triggered_at: new Date().toISOString()
  },
  callback_url: "https://n8n.example.com/webhook/collect-results" // опционально
};
```

### HTTP Request Node: `/n8n/search`
```json
{
  "method": "POST",
  "url": "http://your-server:8000/n8n/search",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": "={{$json}}"
}
```

### Пример ответа
```json
{
  "success": true,
  "query_text": "modelo 303",
  "request_id": "n8n-1728659063",
  "aggregated_results": [
    {
      "text": "Resultado calendar para modelo 303",
      "metadata": {
        "source_type": "calendar",
        "document_id": "calendar-doc",
        "source_url": "https://example.org/calendar/doc"
      },
      "score": 0.95,
      "source_type": "calendar"
    },
    {
      "text": "Resultado news para modelo 303",
      "metadata": {
        "source_type": "news",
        "document_id": "news-doc",
        "source_url": "https://example.org/news/doc"
      },
      "score": 0.95,
      "source_type": "news"
    }
  ],
  "sources": [
    {
      "source": "calendar",
      "results": [ ... ]
    },
    {
      "source": "news",
      "results": [ ... ]
    }
  ],
  "callback_status": "delivered:200"
}
```

### Callback обработка
Если задан `callback_url`, TuExpertoFiscal отправит результаты POST-запросом. В N8N можно добавить отдельный Webhook Trigger, принимающий payload и продолжающий обработку (например, рассылку уведомлений или сохранение в БД).

### Workflow структура:
```
Trigger → Function (Split Query) → HTTP Request 1 (Calendar) → HTTP Request 2 (PDF) → HTTP Request 3 (Telegram) → Function (Aggregate) → Reply
```

### Function Node: Split Query

```javascript
const message = $json.message;
const baseRequest = {
  user_context: {
    channel_type: "telegram",
    channel_user_id: String(message.from.id)
  },
  query_text: message.text,
  top_k: 3,
  generate_response: false  // Не генерируем ответ для каждого источника
};

// Создаем 3 запроса к разным источникам
return [
  { ...baseRequest, filters: { source_types: ["calendar"] }, source_name: "calendar" },
  { ...baseRequest, filters: { source_types: ["pdf", "aeat"] }, source_name: "legal" },
  { ...baseRequest, filters: { source_types: ["telegram"] }, source_name: "community" }
];
```

### Function Node: Aggregate Results

```javascript
// Получаем результаты от всех источников
const calendarResults = $node["HTTP Request 1"].json.results || [];
const legalResults = $node["HTTP Request 2"].json.results || [];
const communityResults = $node["HTTP Request 3"].json.results || [];

// Объединяем и сортируем по score
const allResults = [
  ...calendarResults.map(r => ({...r, category: "📅 Calendario"})),
  ...legalResults.map(r => ({...r, category: "⚖️ Legal"})),
  ...communityResults.map(r => ({...r, category: "👥 Comunidad"}))
].sort((a, b) => b.score - a.score).slice(0, 5);

// Форматируем ответ
let response = "🔍 Resultados de múltiples fuentes:\n\n";

allResults.forEach((result, idx) => {
  response += `${idx + 1}. ${result.category}\n`;
  response += `   ${result.text.substring(0, 100)}...\n`;
  response += `   📊 Score: ${(result.score * 100).toFixed(0)}%\n\n`;
});

return {
  chat_id: $node["Telegram Trigger"].json.message.chat.id,
  text: response,
  parse_mode: "Markdown"
};
```

---

## Сценарий 5: Автоматические уведомления о дедлайнах

### Workflow структура:
```
Cron Trigger (ежедневно) → HTTP Request (Search Calendar) → Function (Filter Upcoming) → Loop (For Each User) → Telegram Notify
```

### Cron Trigger
```
Cron Expression: 0 9 * * *  (каждый день в 9:00)
```

### HTTP Request: Search Upcoming Deadlines

```json
{
  "method": "POST",
  "url": "http://your-server:8000/search",
  "body": {
    "user_context": {
      "channel_type": "system",
      "channel_user_id": "deadline-notifier"
    },
    "query_text": "próximos plazos impuestos",
    "filters": {
      "source_types": ["calendar"],
      "date_from": "{{$now.toISOString()}}",
      "date_to": "{{$now.plus({days: 7}).toISOString()}}"
    },
    "top_k": 10,
    "generate_response": false
  }
}
```

### Function Node: Filter Upcoming

```javascript
const results = $json.results || [];
const today = new Date();
const nextWeek = new Date(today.getTime() + 7*24*60*60*1000);

// Фильтруем дедлайны на следующую неделю
const upcomingDeadlines = results.filter(result => {
  const deadlineDate = new Date(result.metadata.deadline_date);
  return deadlineDate >= today && deadlineDate <= nextWeek;
});

// Группируем по дате
const groupedByDate = upcomingDeadlines.reduce((acc, deadline) => {
  const date = deadline.metadata.deadline_date;
  if (!acc[date]) acc[date] = [];
  acc[date].push(deadline);
  return acc;
}, {});

return Object.entries(groupedByDate).map(([date, deadlines]) => ({
  date,
  deadlines,
  message: formatDeadlineMessage(date, deadlines)
}));

function formatDeadlineMessage(date, deadlines) {
  let msg = `⏰ *Recordatorio de plazos - ${date}*\n\n`;
  deadlines.forEach(d => {
    msg += `📋 ${d.metadata.tax_type}: ${d.text}\n`;
  });
  return msg;
}
```

---

## Сценарий 6: A/B тестирование LLM провайдеров

### Function Node: Random Provider Selection

```javascript
const message = $json.message;
const userId = message.from.id;

// A/B split based on user ID
const useGPT4 = userId % 2 === 0;

return {
  user_context: {
    channel_type: "telegram",
    channel_user_id: String(userId),
    user_metadata: {
      ab_group: useGPT4 ? "gpt4" : "gemini",
      username: message.from.username
    }
  },
  query_text: message.text,
  top_k: 5,
  generate_response: true
};
```

---

## Сценарий 7: Fallback стратегия

### Function Node: Fallback Handler

```javascript
const response = $json;

// Если основной поиск не дал результатов
if (!response.success || response.results.length === 0) {
  // Делаем более широкий поиск
  return {
    user_context: $node["Prepare Request"].json.user_context,
    query_text: $node["Prepare Request"].json.query_text,
    filters: {
      source_types: ["all"],  // Все источники
      only_tax_related: false  // Не только налоговое
    },
    top_k: 10,
    generate_response: true
  };
}

return response;
```

---

## Сценарий 8: Feedback loop (сбор обратной связи)

### Workflow структура:
```
Response Sent → Wait for Feedback → Telegram Callback Query → HTTP Request (Update Feedback) → Supabase Insert
```

### Telegram Send Message with Inline Keyboard

```javascript
const response = $node["HTTP Request"].json;

return {
  chat_id: $node["Telegram Trigger"].json.message.chat.id,
  text: response.generated_response,
  reply_markup: {
    inline_keyboard: [
      [
        { text: "👍 Útil", callback_data: `feedback:useful:${response.session_id}` },
        { text: "👎 No útil", callback_data: `feedback:not_useful:${response.session_id}` }
      ]
    ]
  }
};
```

### Function Node: Process Feedback

```javascript
const callback = $json.callback_query;
const [action, rating, sessionId] = callback.data.split(':');

// Сохраняем feedback в Supabase
return {
  session_id: sessionId,
  user_id: String(callback.from.id),
  rating: rating,
  timestamp: new Date().toISOString()
};
```

---

## Полезные утилиты для N8N

### Function: Log Search Request

```javascript
// Логирование всех запросов
console.log(`[${new Date().toISOString()}] Search request from user ${$json.user_context.channel_user_id}`);
console.log(`Query: ${$json.query_text}`);
console.log(`Filters:`, JSON.stringify($json.filters));

return $json;
```

### Function: Calculate Response Time

```javascript
const startTime = $node["Set Start Time"].json.timestamp;
const endTime = Date.now();
const responseTime = endTime - startTime;

console.log(`Response time: ${responseTime}ms`);

// Добавляем метрику к ответу
return {
  ...$json,
  n8n_response_time_ms: responseTime
};
```

### Function: Error Handler

```javascript
const response = $json;

if (!response.success) {
  // Логируем ошибку
  console.error(`Search failed: ${response.error_message}`);
  
  // Отправляем уведомление админу
  return {
    admin_notification: true,
    error: response.error_message,
    user_id: response.user_id || "unknown",
    query: response.query_text
  };
}

return response;
```

---

## Рекомендации по оптимизации N8N

### 1. Кеширование частых запросов

```javascript
// Function: Check Cache
const cacheKey = `search:${Buffer.from($json.query_text).toString('base64')}`;

// Проверяем Redis cache
// Если есть - возвращаем из кеша
// Если нет - делаем запрос и сохраняем в кеш
```

### 2. Batch processing

Для массовых уведомлений используй batch nodes:

```
Split In Batches (size: 50) → HTTP Request → Delay (1s) → Loop
```

### 3. Rate limiting

Добавь задержки между запросами:

```javascript
// Function: Add Delay
await new Promise(resolve => setTimeout(resolve, 100));
return $json;
```

---

## Мониторинг в N8N

### Webhook для мониторинга

Создай отдельный workflow для мониторинга:

```
Cron (каждые 5 мин)
  ↓
HTTP Request: GET /health
  ↓
IF: status != "healthy"
  ↓
Telegram Send Message (Alert)
```

### Логирование метрик

```javascript
// Function: Log Metrics
const metrics = {
  timestamp: new Date().toISOString(),
  workflow_id: $workflow.id,
  execution_id: $execution.id,
  query_text: $json.query_text,
  results_count: $json.results?.length || 0,
  processing_time_ms: $json.processing_time_ms,
  success: $json.success
};

// Сохрани в InfluxDB/Prometheus/Supabase
console.log('Metrics:', JSON.stringify(metrics));

return $json;
```

---

## Примеры curl для тестирования

### Базовый запрос
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"user_context":{"channel_type":"test","channel_user_id":"123"},"query_text":"IVA"}'
```

### С фильтрами
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "user_context": {"channel_type":"telegram","channel_user_id":"123"},
    "query_text": "modelo 303",
    "filters": {"source_types": ["calendar"], "tax_types": ["IVA"]},
    "top_k": 3
  }'
```

---

**Готово! Теперь у тебя есть все примеры для интеграции с N8N!** 🚀 YO
