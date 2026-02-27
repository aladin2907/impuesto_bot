"""
ResponseGenerator - генерация ответов на основе контекста и типа запроса

Использует специализированные промпты для каждого типа вопроса,
интегрирует контекст из поиска и историю диалога.
"""
import time
from typing import Optional, List, Dict, Any

from app.models.agent import QueryType, Context, AgentResponse, ToolResult
from app.services.llm.llm_service import LLMService
from app.prompts import (
    BASE_SYSTEM_PROMPT,
    TAX_CALENDAR_PROMPT,
    TAX_CALCULATION_PROMPT,
    LEGAL_INTERPRETATION_PROMPT,
    PRACTICAL_ADVICE_PROMPT,
    NEWS_UPDATE_PROMPT,
    GENERAL_INFO_PROMPT
)


# Промпты для каждого типа запроса
QUERY_TYPE_PROMPTS: Dict[QueryType, str] = {
    QueryType.TAX_CALENDAR: TAX_CALENDAR_PROMPT,
    QueryType.TAX_CALCULATION: TAX_CALCULATION_PROMPT,
    QueryType.LEGAL_INTERPRETATION: LEGAL_INTERPRETATION_PROMPT,
    QueryType.PRACTICAL_ADVICE: PRACTICAL_ADVICE_PROMPT,
    QueryType.NEWS_UPDATE: NEWS_UPDATE_PROMPT,
    QueryType.GENERAL_INFO: GENERAL_INFO_PROMPT
}


class ResponseGenerator:
    """
    Генерация ответов агента с учетом типа запроса и контекста

    Features:
    - Специализированные промпты по типу запроса
    - Интеграция контекста из поиска
    - Интеграция результатов инструментов
    - Учет истории диалога
    - Мультиязычная поддержка
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        if llm_service:
            self.llm_service = llm_service
        else:
            self.llm_service = LLMService()
            self.llm_service.initialize()

    async def generate(
        self,
        query: str,
        context: Context,
        query_type: QueryType,
        tools_results: Optional[List[ToolResult]] = None,
        session_history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 1500
    ) -> AgentResponse:
        """
        Генерация ответа агента

        Args:
            query: Запрос пользователя
            context: Контекст из поиска
            query_type: Тип запроса
            tools_results: Результаты инструментов
            session_history: История диалога
            max_tokens: Максимальное количество токенов

        Returns:
            AgentResponse с текстом, источниками, confidence
        """
        start_time = time.time()

        # Собираем системный промпт
        system_prompt = self._build_system_prompt(query_type)

        # Собираем user prompt с контекстом
        user_prompt = self._build_user_prompt(
            query=query,
            context=context,
            tools_results=tools_results,
            session_history=session_history
        )

        # Генерируем ответ через LLM
        response_text = await self.llm_service.generate_async(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens
        )

        processing_time = (time.time() - start_time) * 1000

        return AgentResponse(
            text=response_text,
            query_type=query_type,
            context=context,
            tools_used=tools_results or [],
            confidence=context.confidence_score,
            processing_time_ms=processing_time,
            metadata={
                "sources_count": len(context.results),
                "sources_used": context.sources_used,
                "tools_count": len(tools_results) if tools_results else 0
            }
        )

    def _build_system_prompt(self, query_type: QueryType) -> str:
        """Собрать системный промпт из базового + специфичного для типа"""
        type_prompt = QUERY_TYPE_PROMPTS.get(query_type, QUERY_TYPE_PROMPTS[QueryType.GENERAL_INFO])
        return f"{BASE_SYSTEM_PROMPT}\n\n{type_prompt}"

    def _build_user_prompt(
        self,
        query: str,
        context: Context,
        tools_results: Optional[List[ToolResult]] = None,
        session_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Build user prompt with context, tools and history (English to avoid biasing response language)"""
        parts = []

        # Search context
        if context.results:
            parts.append("## Knowledge base context:\n")
            for i, result in enumerate(context.results[:8], 1):
                source_label = self._get_source_label(result.source)
                content_preview = result.content[:500]

                parts.append(f"### Source {i} ({source_label}):")
                if result.metadata.get('group_name'):
                    parts.append(f"Group: {result.metadata['group_name']}")
                if result.metadata.get('document_title'):
                    parts.append(f"Document: {result.metadata['document_title']}")
                if result.metadata.get('deadline_date'):
                    parts.append(f"Date: {result.metadata['deadline_date']}")
                if result.metadata.get('article_title'):
                    parts.append(f"Article: {result.metadata['article_title']}")

                parts.append(f"{content_preview}\n")

        # Tool results
        if tools_results:
            parts.append("\n## Tool results:\n")
            for tool_result in tools_results:
                if tool_result.success:
                    parts.append(f"### {tool_result.tool_type}:")
                    parts.append(f"{tool_result.result}\n")

        # Conversation history
        if session_history and len(session_history) > 0:
            parts.append("\n## Recent conversation history:\n")
            for msg in session_history[-3:]:
                role = "User" if msg.get("role") == "user" else "Assistant"
                parts.append(f"{role}: {msg.get('content', '')[:200]}")
            parts.append("")

        # The actual query
        parts.append(f"\n## User question (respond in the SAME language as this question):\n{query}")

        return "\n".join(parts)

    def _get_source_label(self, source: str) -> str:
        """Source label (English to not bias response language)"""
        labels = {
            "telegram": "Telegram Community",
            "pdf": "Legal Document",
            "calendar": "Tax Calendar",
            "news": "News"
        }
        return labels.get(source, source)
