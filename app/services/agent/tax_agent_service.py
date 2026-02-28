"""
TaxAgentService - главный оркестратор AI налогового консультанта

Координирует все компоненты агента:
1. Классификация запроса
2. Получение контекста (адаптивный поиск)
3. Генерация ответа (специализированные промпты)
4. Управление сессиями
"""
import time
import logging
from typing import Optional, List, Dict, Callable, Awaitable

from app.models.agent import (
    QueryType, AgentRequest, AgentResponse, Context,
    ToolResult, SearchSource
)
from app.services.agent.query_classifier import QueryClassifier
from app.services.agent.context_retriever import ContextRetriever
from app.services.agent.response_generator import ResponseGenerator
from app.services.agent.tool_executor import ToolExecutor
from app.services.search.unified_search_service import UnifiedSearchService
from app.services.llm.llm_service import LLMService
from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)


class TaxAgentService:
    """
    Главный оркестратор AI налогового агента

    Flow:
    1. User sends query
    2. QueryClassifier determines query type
    3. ContextRetriever searches relevant sources with adaptive weights
    4. ResponseGenerator creates answer with specialized prompts
    5. Session manager saves interaction to history
    """

    def __init__(self):
        # LLM Service (gpt-4.1 for responses)
        self.llm_service = LLMService()
        self.llm_service.initialize()

        # Search Service
        self.search_service = UnifiedSearchService()

        # Agent Components
        self.classifier = QueryClassifier()  # gpt-4.1-mini for classification
        self.retriever = ContextRetriever(
            search_service=self.search_service,
            classifier=self.classifier
        )
        self.generator = ResponseGenerator(llm_service=self.llm_service)
        self.tool_executor = ToolExecutor()  # Tools: calculator, calendar, documents

        # Database service for sessions/users
        self.db = SupabaseService()

        self._initialized = False
        logger.info("TaxAgentService created")

    async def initialize(self) -> bool:
        """Инициализация всех сервисов"""
        try:
            self.db.connect()
            self._initialized = True
            logger.info("✅ TaxAgentService initialized")
            return True
        except Exception as e:
            logger.error(f"❌ TaxAgentService initialization error: {e}")
            # Работаем и без БД - просто без сессий
            self._initialized = True
            return True

    async def process_query(
        self,
        query: str,
        user_id: str,
        session_id: Optional[str] = None,
        include_tools: bool = True,
        max_context_items: int = 10,
        progress_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> AgentResponse:
        """
        Основной метод обработки запроса пользователя

        Args:
            query: Текст запроса (любой язык)
            user_id: ID пользователя (telegram_id)
            session_id: ID сессии (если есть)
            include_tools: Использовать инструменты
            max_context_items: Макс. количество контекстных элементов

        Returns:
            AgentResponse с текстом ответа, источниками и метаданными
        """
        total_start = time.time()

        logger.info(f"Processing query from user {user_id}: {query[:100]}...")

        try:
            # Шаг 1: Классификация + поиск контекста
            if progress_callback:
                await progress_callback("search")
            context, classification = await self.retriever.retrieve(
                query=query,
                top_k=max_context_items,
                similarity_threshold=0.4
            )

            logger.info(
                f"Classification: {classification.query_type} "
                f"(confidence={classification.confidence:.2f}, "
                f"time={classification.classification_time_ms:.0f}ms)"
            )

            # Шаг 2: Выполнение инструментов
            tools_results = []
            if include_tools:
                if progress_callback:
                    await progress_callback("tools")
                tools_results = await self.tool_executor.execute_tools(
                    query=query,
                    query_type=classification.query_type
                )
                if tools_results:
                    logger.info(
                        f"Tools executed: {len(tools_results)} results, "
                        f"{sum(1 for t in tools_results if t.success)} successful"
                    )

            # Шаг 3: Получение истории диалога (если есть сессия)
            session_history = None
            if session_id:
                session_history = await self._get_session_history(
                    user_id=user_id,
                    session_id=session_id
                )

            # Шаг 4: Генерация ответа
            if progress_callback:
                await progress_callback("generate")
            response = await self.generator.generate(
                query=query,
                context=context,
                query_type=classification.query_type,
                tools_results=tools_results if tools_results else None,
                session_history=session_history
            )

            # Шаг 5: Сохранение в историю (async, не блокирует)
            total_time = (time.time() - total_start) * 1000
            response.processing_time_ms = total_time

            try:
                await self._save_interaction(
                    user_id=user_id,
                    session_id=session_id,
                    query=query,
                    response=response
                )
            except Exception as e:
                logger.warning(f"Failed to save interaction: {e}")

            logger.info(
                f"✅ Response generated in {total_time:.0f}ms "
                f"(type={classification.query_type}, "
                f"confidence={response.confidence:.2f}, "
                f"sources={len(context.results)})"
            )

            return response

        except Exception as e:
            total_time = (time.time() - total_start) * 1000
            logger.error(f"❌ Error processing query: {e}")

            return AgentResponse(
                text=self._get_error_message(query),
                query_type=QueryType.GENERAL_INFO,
                context=Context(
                    results=[],
                    sources_used=[],
                    confidence_score=0.0,
                    total_results=0
                ),
                tools_used=[],
                confidence=0.0,
                processing_time_ms=total_time,
                metadata={"error": str(e)}
            )

    async def _get_session_history(
        self,
        user_id: str,
        session_id: str
    ) -> Optional[List[Dict[str, str]]]:
        """Получить историю сессии из БД"""
        try:
            messages = self.db.get_user_messages(user_id, limit=6)
            if not messages:
                return None

            history = []
            for msg in messages:
                if msg.get('query_text'):
                    history.append({"role": "user", "content": msg['query_text']})
                if msg.get('response_text'):
                    history.append({"role": "assistant", "content": msg['response_text']})

            return history if history else None

        except Exception as e:
            logger.warning(f"Failed to get session history: {e}")
            return None

    async def _save_interaction(
        self,
        user_id: str,
        session_id: Optional[str],
        query: str,
        response: AgentResponse
    ):
        """Сохранить запрос и ответ в историю"""
        try:
            sources = [
                {
                    "source": r.source,
                    "similarity": r.similarity_score
                }
                for r in response.context.results[:5]
            ]

            self.db.save_message(
                user_id=user_id,
                session_id=session_id or "default",
                query_text=query,
                response_text=response.text,
                sources=sources,
                is_relevant=response.confidence > 0.5
            )
        except Exception as e:
            logger.warning(f"Failed to save message: {e}")

    def _get_error_message(self, query: str) -> str:
        """Сообщение об ошибке на языке пользователя"""
        if any('\u0400' <= c <= '\u04FF' for c in query):
            return (
                "Извините, произошла ошибка при обработке вашего запроса. "
                "Пожалуйста, попробуйте переформулировать вопрос или "
                "попробуйте позже."
            )
        return (
            "Lo siento, ha ocurrido un error al procesar tu consulta. "
            "Por favor, intenta reformular tu pregunta o "
            "inténtalo más tarde."
        )

    async def health_check(self) -> Dict:
        """Проверка состояния всех компонентов"""
        return {
            "status": "ok" if self._initialized else "not_initialized",
            "llm_provider": self.llm_service.provider,
            "llm_model": self.llm_service.model,
            "search_service": "ok",
            "classifier": "ok",
            "database": "ok" if self.db else "not_connected"
        }
