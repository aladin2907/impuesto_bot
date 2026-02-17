"""
ContextRetriever - адаптивный поиск контекста по типу запроса

Координирует поиск по всем источникам через UnifiedSearchService,
переводит запросы для Calendar/PDF, применяет адаптивные веса.
"""
import time
from typing import Optional, List

from app.models.agent import (
    QueryType, Context, SearchSource, ClassificationResult
)
from app.services.search.unified_search_service import UnifiedSearchService
from app.services.agent.query_classifier import QueryClassifier


class ContextRetriever:
    """
    Интеллектуальный поиск контекста для агента

    Features:
    - Классификация запроса (если не предоставлена)
    - Перевод ключевых терминов на испанский для Calendar/PDF
    - Адаптивные веса источников
    - Параллельный поиск
    """

    def __init__(
        self,
        search_service: Optional[UnifiedSearchService] = None,
        classifier: Optional[QueryClassifier] = None
    ):
        self.search_service = search_service or UnifiedSearchService()
        self.classifier = classifier or QueryClassifier()

    async def retrieve(
        self,
        query: str,
        query_type: Optional[QueryType] = None,
        top_k: int = 10,
        similarity_threshold: float = 0.4,
        sources: Optional[List[SearchSource]] = None
    ) -> tuple[Context, ClassificationResult]:
        """
        Получение контекста для генерации ответа

        Args:
            query: Запрос пользователя (любой язык)
            query_type: Тип запроса (если уже классифицирован)
            top_k: Количество результатов
            similarity_threshold: Минимальный порог схожести
            sources: Конкретные источники (None = все)

        Returns:
            Tuple[Context, ClassificationResult]
        """
        start_time = time.time()

        # Шаг 1: Классификация + перевод (если нужно)
        if query_type:
            classification = ClassificationResult(
                query_type=query_type,
                confidence=1.0,
                reasoning="Pre-classified",
                classification_time_ms=0
            )
            search_query = query
        else:
            # Классифицируем и получаем ключевые слова на испанском
            classification, search_query = await self.classifier.classify_with_translation(query)

        # Шаг 2: Поиск по всем источникам с адаптивными весами
        # Передаем оригинальный запрос для Telegram, переведённый - для Calendar/PDF/News
        context = await self.search_service.search_all(
            query=search_query,
            query_type=classification.query_type,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            sources=sources,
            original_query=query  # Оригинальный запрос для Telegram
        )

        # Шаг 3: Если нашли мало результатов, пробуем оригинальный запрос везде
        if context.total_results < 3 and search_query != query:
            fallback_context = await self.search_service.search_all(
                query=query,
                query_type=classification.query_type,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                sources=sources,
                original_query=query
            )
            # Берем лучший результат
            if fallback_context.total_results > context.total_results:
                context = fallback_context

        processing_time = (time.time() - start_time) * 1000
        print(f"📚 Context retrieved in {processing_time:.0f}ms: "
              f"{context.total_results} results, "
              f"confidence={context.confidence_score:.2f}, "
              f"type={classification.query_type}")

        return context, classification
