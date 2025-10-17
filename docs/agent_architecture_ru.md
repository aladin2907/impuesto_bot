# TuExpertoFiscal NAIL: Архитектура ИИ-агента

## 🎯 Обзор системы

TuExpertoFiscal NAIL - это интеллектуальный налоговый агент для Испании, который использует передовые технологии ИИ для предоставления точных и актуальных ответов на налоговые вопросы. Агент построен на архитектуре RAG (Retrieval-Augmented Generation) и интегрирован с множественными источниками данных.

## 🏗️ Архитектура агента

### Основные компоненты

```
┌─────────────────────────────────────────────────────────────┐
│                    Пользовательский интерфейс                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Telegram  │  │  WhatsApp   │  │   Web API   │         │
│  │     Bot     │  │     Bot     │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Router    │  │  Auth &     │  │   Session   │         │
│  │  Handler    │  │  Users      │  │  Manager    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    ИИ-ядро агента                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Query     │  │   Context   │  │   Response  │         │
│  │ Classifier  │  │  Retrieval  │  │  Generator  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    База знаний                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │Elasticsearch│  │  Supabase   │  │   Vector    │         │
│  │  (Search)   │  │(Metadata)   │  │   Store     │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## 🧠 Логика работы агента

### 1. Обработка входящего запроса

```python
class TaxAgent:
    def __init__(self):
        self.query_classifier = QueryClassifier()
        self.context_retriever = ContextRetriever()
        self.response_generator = ResponseGenerator()
        self.session_manager = SessionManager()
    
    async def process_query(self, user_query: str, user_id: str, session_id: str):
        # 1. Классификация запроса
        query_type = await self.query_classifier.classify(user_query)
        
        # 2. Получение контекста
        context = await self.context_retriever.retrieve(
            query=user_query,
            query_type=query_type,
            user_profile=await self.get_user_profile(user_id)
        )
        
        # 3. Генерация ответа
        response = await self.response_generator.generate(
            query=user_query,
            context=context,
            query_type=query_type,
            session_history=await self.session_manager.get_history(session_id)
        )
        
        # 4. Сохранение в историю
        await self.session_manager.save_interaction(
            session_id=session_id,
            user_query=user_query,
            agent_response=response,
            context_sources=context.sources
        )
        
        return response
```

### 2. Классификация запросов

Агент определяет тип запроса для оптимизации поиска:

```python
class QueryClassifier:
    QUERY_TYPES = {
        "tax_calendar": "Вопросы о сроках и дедлайнах",
        "tax_calculation": "Расчеты налогов и сборов", 
        "legal_interpretation": "Толкование законов и норм",
        "practical_advice": "Практические советы и рекомендации",
        "news_update": "Актуальные новости и изменения",
        "general_info": "Общая информация о налогах"
    }
    
    async def classify(self, query: str) -> str:
        # Используем быструю LLM для классификации
        classification_prompt = f"""
        Классифицируй следующий налоговый вопрос по типу:
        
        Вопрос: {query}
        
        Типы:
        - tax_calendar: сроки, дедлайны, календарь
        - tax_calculation: расчеты, суммы, формулы
        - legal_interpretation: законы, нормы, толкование
        - practical_advice: советы, рекомендации, как делать
        - news_update: новости, изменения, обновления
        - general_info: общая информация
        
        Ответь только одним словом - типом запроса.
        """
        
        result = await self.llm_service.generate(classification_prompt)
        return result.strip().lower()
```

### 3. Извлечение контекста

Агент использует гибридный поиск для нахождения релевантной информации:

```python
class ContextRetriever:
    def __init__(self):
        self.elasticsearch = ElasticsearchService()
        self.supabase = SupabaseService()
        self.vector_store = VectorStore()
    
    async def retrieve(self, query: str, query_type: str, user_profile: dict) -> Context:
        # Определяем приоритетные источники для типа запроса
        source_weights = self._get_source_weights(query_type)
        
        # Параллельный поиск по всем источникам
        search_tasks = []
        
        if source_weights["calendar"] > 0:
            search_tasks.append(
                self._search_calendar(query, user_profile)
            )
        
        if source_weights["telegram"] > 0:
            search_tasks.append(
                self._search_telegram(query, user_profile)
            )
        
        if source_weights["pdf_documents"] > 0:
            search_tasks.append(
                self._search_pdf_documents(query, user_profile)
            )
        
        if source_weights["news"] > 0:
            search_tasks.append(
                self._search_news(query, user_profile)
            )
        
        # Выполняем поиск параллельно
        search_results = await asyncio.gather(*search_tasks)
        
        # Объединяем и ранжируем результаты
        ranked_results = self._rank_and_merge_results(
            search_results, source_weights
        )
        
        return Context(
            content=ranked_results,
            sources=self._extract_sources(ranked_results),
            confidence_score=self._calculate_confidence(ranked_results)
        )
    
    def _get_source_weights(self, query_type: str) -> dict:
        """Определяем веса источников для разных типов запросов"""
        weights = {
            "tax_calendar": {"calendar": 0.7, "telegram": 0.2, "pdf_documents": 0.1, "news": 0.0},
            "tax_calculation": {"calendar": 0.2, "telegram": 0.3, "pdf_documents": 0.4, "news": 0.1},
            "legal_interpretation": {"calendar": 0.1, "telegram": 0.2, "pdf_documents": 0.6, "news": 0.1},
            "practical_advice": {"calendar": 0.2, "telegram": 0.5, "pdf_documents": 0.2, "news": 0.1},
            "news_update": {"calendar": 0.1, "telegram": 0.3, "pdf_documents": 0.1, "news": 0.5},
            "general_info": {"calendar": 0.2, "telegram": 0.3, "pdf_documents": 0.3, "news": 0.2}
        }
        return weights.get(query_type, weights["general_info"])
```

### 4. Генерация ответа

Агент формирует персонализированный ответ на основе контекста:

```python
class ResponseGenerator:
    def __init__(self):
        self.llm_service = LLMService()
        self.template_engine = TemplateEngine()
    
    async def generate(self, query: str, context: Context, query_type: str, session_history: list) -> Response:
        # Формируем промпт на основе типа запроса
        system_prompt = self._get_system_prompt(query_type)
        
        # Создаем контекст для LLM
        context_text = self._format_context(context)
        
        # Добавляем историю диалога если есть
        history_text = self._format_history(session_history)
        
        # Генерируем ответ
        full_prompt = f"""
        {system_prompt}
        
        Контекст из базы знаний:
        {context_text}
        
        История диалога:
        {history_text}
        
        Вопрос пользователя: {query}
        
        Сгенерируй точный, полезный ответ с указанием источников.
        """
        
        response_text = await self.llm_service.generate(full_prompt)
        
        return Response(
            text=response_text,
            sources=context.sources,
            confidence=context.confidence_score,
            query_type=query_type,
            metadata={
                "context_items_used": len(context.content),
                "response_time": time.time() - start_time
            }
        )
    
    def _get_system_prompt(self, query_type: str) -> str:
        """Системные промпты для разных типов запросов"""
        prompts = {
            "tax_calendar": """
            Ты эксперт по налоговому календарю Испании. Отвечай точно на вопросы о сроках, 
            дедлайнах и календарных событиях. Всегда указывай конкретные даты и источники.
            """,
            "tax_calculation": """
            Ты налоговый консультант по расчетам в Испании. Помогай с расчетами налогов, 
            сборов и взносов. Показывай формулы и примеры расчетов. Всегда предупреждай, 
            что это общая информация и нужна консультация специалиста.
            """,
            "legal_interpretation": """
            Ты юрист-эксперт по налоговому праву Испании. Толкуй законы и нормы точно, 
            ссылаясь на конкретные статьи и документы. Различай обязательные и рекомендательные нормы.
            """,
            "practical_advice": """
            Ты практикующий налоговый консультант. Давай практические советы на основе 
            опыта сообщества и лучших практик. Всегда подчеркивай важность индивидуальной консультации.
            """,
            "news_update": """
            Ты аналитик налоговых новостей Испании. Предоставляй актуальную информацию 
            о изменениях в законодательстве, новых требованиях и важных событиях.
            """,
            "general_info": """
            Ты всесторонний эксперт по налогам Испании. Отвечай на общие вопросы, 
            предоставляя структурированную и понятную информацию.
            """
        }
        return prompts.get(query_type, prompts["general_info"])
```

## 🔄 Жизненный цикл запроса

### Пошаговый процесс

1. **Получение запроса** - Пользователь отправляет вопрос через Telegram/WhatsApp/API
2. **Аутентификация** - Проверка пользователя и его подписки
3. **Классификация** - Определение типа запроса (0.1-0.3 сек)
4. **Поиск контекста** - Гибридный поиск по базе знаний (0.5-1.0 сек)
5. **Генерация ответа** - LLM создает персонализированный ответ (1.0-3.0 сек)
6. **Постобработка** - Форматирование, добавление источников (0.1-0.2 сек)
7. **Сохранение** - Запись в историю диалога
8. **Отправка** - Возврат ответа пользователю

### Временные характеристики

```
Общее время ответа: 2-5 секунд
├── Классификация: 0.1-0.3 сек
├── Поиск контекста: 0.5-1.0 сек
├── Генерация ответа: 1.0-3.0 сек
├── Постобработка: 0.1-0.2 сек
└── Сохранение: 0.1-0.2 сек
```

## 🎯 Типы запросов и обработка

### 1. Календарные запросы
**Пример:** "Когда нужно подать IVA за 3 квартал?"

**Обработка:**
- Приоритет: Календарь (70%) + Telegram (20%) + PDF (10%)
- Поиск по датам, кварталам, типам налогов
- Ответ с конкретными датами и напоминаниями

### 2. Расчетные запросы  
**Пример:** "Сколько заплатить IRPF с 50000 евро?"

**Обработка:**
- Приоритет: PDF документы (40%) + Telegram (30%) + Календарь (20%) + Новости (10%)
- Поиск формул, ставок, примеров расчетов
- Ответ с пошаговым расчетом и предупреждениями

### 3. Правовые вопросы
**Пример:** "Что говорит закон о налоговых льготах для автономос?"

**Обработка:**
- Приоритет: PDF документы (60%) + Telegram (20%) + Календарь (10%) + Новости (10%)
- Поиск конкретных статей, законов, постановлений
- Ответ с цитатами и ссылками на документы

### 4. Практические советы
**Пример:** "Как лучше организовать документооборот для автономос?"

**Обработка:**
- Приоритет: Telegram (50%) + PDF (20%) + Календарь (20%) + Новости (10%)
- Поиск опыта сообщества, лучших практик
- Ответ с практическими рекомендациями

### 5. Новостные запросы
**Пример:** "Какие изменения в налогах ожидаются в 2025?"

**Обработка:**
- Приоритет: Новости (50%) + Telegram (30%) + PDF (10%) + Календарь (10%)
- Поиск актуальных новостей, изменений
- Ответ с последними обновлениями

## 🧩 Интеграция с существующей системой

### Использование текущих сервисов

```python
# app/services/agent/
class TaxAgentService:
    def __init__(self):
        # Используем существующие сервисы
        self.llm_service = LLMService()  # app/services/llm/
        self.elasticsearch_service = ElasticsearchService()  # app/services/elasticsearch/
        self.supabase_service = SupabaseService()  # app/services/supabase_service.py
        
        # Новые компоненты агента
        self.query_classifier = QueryClassifier(self.llm_service)
        self.context_retriever = ContextRetriever(
            self.elasticsearch_service, 
            self.supabase_service
        )
        self.response_generator = ResponseGenerator(self.llm_service)
        self.session_manager = SessionManager(self.supabase_service)
    
    async def process_user_query(self, query: str, user_id: str, platform: str):
        """Основной метод обработки запросов пользователей"""
        try:
            # Получаем или создаем сессию
            session_id = await self.session_manager.get_or_create_session(
                user_id=user_id,
                platform=platform
            )
            
            # Обрабатываем запрос
            response = await self.process_query(query, user_id, session_id)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return self._get_error_response()
```

### Интеграция с FastAPI

```python
# app/main.py
from app.services.agent import TaxAgentService

app = FastAPI()
agent_service = TaxAgentService()

@app.post("/api/v1/query")
async def handle_query(request: QueryRequest):
    """Обработка запросов от пользователей"""
    response = await agent_service.process_user_query(
        query=request.query,
        user_id=request.user_id,
        platform=request.platform
    )
    return response

@app.post("/webhook/telegram")
async def telegram_webhook(update: dict):
    """Webhook для Telegram бота"""
    message = update.get("message", {})
    user_id = message.get("from", {}).get("id")
    query = message.get("text", "")
    
    response = await agent_service.process_user_query(
        query=query,
        user_id=str(user_id),
        platform="telegram"
    )
    
    # Отправляем ответ в Telegram
    await send_telegram_message(user_id, response.text)
```

## 📊 Мониторинг и аналитика

### Метрики производительности

```python
class AgentMetrics:
    def __init__(self):
        self.metrics = {
            "total_queries": 0,
            "response_times": [],
            "query_types": {},
            "confidence_scores": [],
            "error_rate": 0,
            "user_satisfaction": 0
        }
    
    async def track_query(self, query_type: str, response_time: float, confidence: float):
        """Отслеживание метрик запроса"""
        self.metrics["total_queries"] += 1
        self.metrics["response_times"].append(response_time)
        self.metrics["query_types"][query_type] = self.metrics["query_types"].get(query_type, 0) + 1
        self.metrics["confidence_scores"].append(confidence)
        
        # Сохраняем в Supabase для аналитики
        await self.supabase_service.table("agent_metrics").insert({
            "query_type": query_type,
            "response_time": response_time,
            "confidence_score": confidence,
            "timestamp": datetime.utcnow()
        }).execute()
```

### Логирование и отладка

```python
import logging
from app.config.settings import settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/agent.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class AgentLogger:
    @staticmethod
    def log_query_processing(user_id: str, query: str, query_type: str, response_time: float):
        """Логирование обработки запроса"""
        logger.info(f"Query processed - User: {user_id}, Type: {query_type}, Time: {response_time:.2f}s")
    
    @staticmethod
    def log_error(error: Exception, context: dict):
        """Логирование ошибок"""
        logger.error(f"Agent error: {error}, Context: {context}")
```

## 🚀 Развертывание и масштабирование

### Конфигурация для продакшена

```python
# app/config/agent_settings.py
class AgentSettings:
    # LLM настройки
    DEFAULT_LLM_PROVIDER = "openai"
    FALLBACK_LLM_PROVIDER = "gemini"
    
    # Поиск настройки
    MAX_CONTEXT_ITEMS = 10
    MIN_CONFIDENCE_SCORE = 0.7
    
    # Производительность
    MAX_RESPONSE_TIME = 5.0  # секунд
    CACHE_TTL = 300  # секунд
    
    # Безопасность
    MAX_QUERIES_PER_MINUTE = 10
    BLOCKED_QUERIES = ["hack", "exploit", "bypass"]
```

### Горизонтальное масштабирование

```python
# Использование Redis для кеширования
import redis
from app.config.settings import settings

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0
)

class AgentCache:
    def __init__(self):
        self.redis = redis_client
    
    async def get_cached_response(self, query_hash: str):
        """Получение кешированного ответа"""
        cached = self.redis.get(f"agent_response:{query_hash}")
        return json.loads(cached) if cached else None
    
    async def cache_response(self, query_hash: str, response: dict, ttl: int = 300):
        """Кеширование ответа"""
        self.redis.setex(
            f"agent_response:{query_hash}",
            ttl,
            json.dumps(response)
        )
```

## 🔮 Будущие улучшения

### Планируемые функции

1. **Мультиязычность** - Поддержка испанского, английского, русского
2. **Голосовые запросы** - Интеграция с speech-to-text
3. **Персонализация** - Адаптация под профиль пользователя
4. **Прогнозирование** - Предсказание налоговых событий
5. **Интеграция с банками** - Автоматический импорт транзакций
6. **Мобильное приложение** - Нативное iOS/Android приложение

### Технические улучшения

1. **Федеративный поиск** - Поиск по внешним источникам
2. **Онлайн обучение** - Адаптация на основе обратной связи
3. **Мультимодальность** - Обработка изображений и документов
4. **Объяснимость** - Детальное объяснение логики ответов
5. **A/B тестирование** - Оптимизация промптов и алгоритмов

---

*Разработано NAIL - Nahornyi AI Lab*

YO
