"""
Unified Search Service - координирует поиск по всем источникам данных
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, date

from app.models.agent import SearchSource, SearchResult, Context, QueryType, SOURCE_WEIGHTS
from app.repositories.telegram_repository import TelegramRepository
from app.repositories.pdf_repository import PDFRepository
from app.repositories.calendar_repository import CalendarRepository
from app.repositories.news_repository import NewsRepository
from app.services.llm.llm_service import LLMService
from app.services.embeddings.huggingface_embeddings import HuggingFaceEmbeddings


class UnifiedSearchService:
    """
    Унифицированный сервис поиска по всем источникам данных

    Features:
    - Multi-source parallel search
    - Adaptive source weighting by query type
    - Different embeddings for different sources
    - Result merging and ranking
    """

    def __init__(self):
        """Initialize repositories and embedding services"""
        # Repositories
        self.telegram_repo = TelegramRepository()
        self.pdf_repo = PDFRepository()
        self.calendar_repo = CalendarRepository()
        self.news_repo = NewsRepository()

        # Embedding services
        self.llm_service = LLMService()
        self.llm_service.initialize()  # OpenAI embeddings (1536d) for PDF/News

        # HuggingFace embeddings (1024d) for Telegram
        try:
            self.hf_embeddings = HuggingFaceEmbeddings()
        except Exception as e:
            print(f"⚠️ HuggingFace embeddings not available: {e}")
            self.hf_embeddings = None

        print("✅ UnifiedSearchService initialized")

    async def search_all(
        self,
        query: str,
        query_type: QueryType = QueryType.GENERAL_INFO,
        top_k: int = 10,
        similarity_threshold: float = 0.5,
        sources: Optional[List[SearchSource]] = None,
        original_query: Optional[str] = None
    ) -> Context:
        """
        Поиск по всем источникам с адаптивными весами

        Args:
            query: Поисковый запрос (переведённый на испанский для Calendar/PDF)
            query_type: Тип запроса (определяет веса источников)
            top_k: Количество результатов на источник
            similarity_threshold: Минимальный порог схожести
            sources: Конкретные источники для поиска (None = все)
            original_query: Оригинальный запрос пользователя (для Telegram на русском)

        Returns:
            Context с результатами, confidence score, sources used
        """
        start_time = datetime.now()

        # Получаем веса источников для данного типа запроса
        source_weights = SOURCE_WEIGHTS.get(query_type, SOURCE_WEIGHTS[QueryType.GENERAL_INFO])

        # Фильтруем источники если указаны
        if sources:
            source_weights = {src: weight for src, weight in source_weights.items() if src in sources}

        # Фильтруем источники с нулевым весом
        active_sources = {src: weight for src, weight in source_weights.items() if weight > 0}

        # Используем оригинальный запрос для Telegram (русский), переведённый для остальных
        telegram_query = original_query if original_query else query

        # Параллельный поиск по всем активным источникам
        search_tasks = []
        for source, weight in active_sources.items():
            if source == SearchSource.TELEGRAM:
                search_tasks.append(self._search_telegram(telegram_query, top_k, similarity_threshold))
            elif source == SearchSource.PDF:
                search_tasks.append(self._search_pdf(query, top_k, similarity_threshold))
            elif source == SearchSource.CALENDAR:
                search_tasks.append(self._search_calendar(query, top_k))
            elif source == SearchSource.NEWS:
                search_tasks.append(self._search_news(query, top_k, similarity_threshold))

        # Выполняем все поиски параллельно
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Обрабатываем результаты
        all_results: List[SearchResult] = []
        sources_used: List[SearchSource] = []

        for i, (source, weight) in enumerate(active_sources.items()):
            results = search_results[i]

            # Проверяем на ошибки
            if isinstance(results, Exception):
                print(f"⚠️ Error searching {source}: {results}")
                continue

            if results:
                sources_used.append(source)

                # Применяем веса к relevance score
                for result in results:
                    result.relevance_score = (result.similarity_score or 0.5) * weight
                    all_results.append(result)

        # Сортируем по relevance score
        all_results.sort(key=lambda x: x.relevance_score or 0, reverse=True)

        # Берем топ-K результатов
        top_results = all_results[:top_k]

        # Вычисляем confidence score
        confidence_score = self._calculate_confidence(top_results, sources_used, active_sources)

        # Создаем контекст
        context = Context(
            results=top_results,
            sources_used=sources_used,
            confidence_score=confidence_score,
            total_results=len(all_results)
        )

        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        print(f"✅ Search completed in {processing_time:.0f}ms: {len(top_results)} results from {len(sources_used)} sources")

        return context

    async def _search_telegram(
        self,
        query: str,
        limit: int,
        similarity_threshold: float
    ) -> List[SearchResult]:
        """Поиск по Telegram тредам (HuggingFace embeddings, 1024d)"""
        try:
            if not self.hf_embeddings:
                print("⚠️ HuggingFace embeddings not available, skipping Telegram search")
                return []

            # Генерируем embedding через HuggingFace (1024d)
            query_embedding = self.hf_embeddings.generate(query, prefix="query: ")
            if not query_embedding:
                return []

            # Hybrid search через RPC
            results = await self.telegram_repo.hybrid_search(
                query_text=query,
                query_embedding=query_embedding,
                limit=limit,
                similarity_threshold=similarity_threshold
            )

            # Преобразуем в SearchResult
            search_results = []
            for result in results:
                search_results.append(SearchResult(
                    source=SearchSource.TELEGRAM,
                    content=result.get('content', ''),
                    metadata={
                        'thread_id': result.get('thread_id'),
                        'group_name': result.get('group_name'),
                        'quality_score': result.get('quality_score'),
                        'message_count': result.get('message_count')
                    },
                    similarity_score=result.get('similarity', 0.5)
                ))

            return search_results

        except Exception as e:
            print(f"⚠️ Error in Telegram search: {e}")
            return []

    async def _search_pdf(
        self,
        query: str,
        limit: int,
        similarity_threshold: float
    ) -> List[SearchResult]:
        """Поиск по PDF документам (OpenAI embeddings, 1536d)"""
        try:
            # Генерируем embedding через OpenAI (1536d)
            query_embedding = await self._generate_openai_embedding(query)
            if not query_embedding:
                return []

            # Hybrid search через RPC
            results = await self.pdf_repo.hybrid_search(
                query_text=query,
                query_embedding=query_embedding,
                limit=limit,
                similarity_threshold=similarity_threshold
            )

            # Преобразуем в SearchResult
            search_results = []
            for result in results:
                search_results.append(SearchResult(
                    source=SearchSource.PDF,
                    content=result.get('content', ''),
                    metadata={
                        'document_title': result.get('document_title'),
                        'chunk_number': result.get('chunk_number'),
                        'document_type': result.get('document_type'),
                        'region': result.get('region'),
                        'categories': result.get('categories')
                    },
                    similarity_score=result.get('similarity', 0.5)
                ))

            return search_results

        except Exception as e:
            print(f"⚠️ Error in PDF search: {e}")
            return []

    async def _search_calendar(
        self,
        query: str,
        limit: int
    ) -> List[SearchResult]:
        """Поиск по налоговому календарю (keyword search, no embeddings)"""
        try:
            # Keyword search через repository
            results = await self.calendar_repo.search_by_query(
                query_text=query,
                limit=limit
            )

            # Преобразуем в SearchResult
            search_results = []
            for result in results:
                # Для календаря нет similarity score, используем фиксированный
                search_results.append(SearchResult(
                    source=SearchSource.CALENDAR,
                    content=f"{result.get('description', '')} (Deadline: {result.get('deadline_date')})",
                    metadata={
                        'deadline_date': result.get('deadline_date'),
                        'tax_type': result.get('tax_type'),
                        'tax_model': result.get('tax_model'),
                        'applies_to': result.get('applies_to'),
                        'region': result.get('region')
                    },
                    similarity_score=0.7  # Fixed score for calendar results
                ))

            return search_results

        except Exception as e:
            print(f"⚠️ Error in Calendar search: {e}")
            return []

    async def _search_news(
        self,
        query: str,
        limit: int,
        similarity_threshold: float
    ) -> List[SearchResult]:
        """Поиск по новостям (OpenAI embeddings, 1536d)"""
        try:
            # Генерируем embedding через OpenAI (1536d)
            query_embedding = await self._generate_openai_embedding(query)
            if not query_embedding:
                return []

            # Hybrid search через RPC
            results = await self.news_repo.hybrid_search(
                query_text=query,
                query_embedding=query_embedding,
                limit=limit,
                similarity_threshold=similarity_threshold
            )

            # Преобразуем в SearchResult
            search_results = []
            for result in results:
                search_results.append(SearchResult(
                    source=SearchSource.NEWS,
                    content=result.get('content', ''),
                    metadata={
                        'article_title': result.get('article_title'),
                        'article_url': result.get('article_url'),
                        'published_at': result.get('published_at'),
                        'news_source': result.get('news_source'),
                        'categories': result.get('categories')
                    },
                    similarity_score=result.get('similarity', 0.5)
                ))

            return search_results

        except Exception as e:
            print(f"⚠️ Error in News search: {e}")
            return []

    async def _generate_openai_embedding(self, text: str) -> Optional[List[float]]:
        """Генерация embedding через OpenAI API (1536d)"""
        try:
            if not self.llm_service.embeddings_model:
                print("⚠️ OpenAI embeddings not available")
                return None

            # LangChain OpenAIEmbeddings.embed_query() возвращает список
            embedding = await asyncio.to_thread(
                self.llm_service.embeddings_model.embed_query,
                text
            )

            return embedding

        except Exception as e:
            print(f"⚠️ Error generating OpenAI embedding: {e}")
            return None

    def _calculate_confidence(
        self,
        results: List[SearchResult],
        sources_used: List[SearchSource],
        active_sources: Dict[SearchSource, float]
    ) -> float:
        """
        Вычисление confidence score на основе результатов

        Факторы:
        - Количество найденных результатов
        - Similarity scores результатов
        - Количество использованных источников
        """
        if not results:
            return 0.0

        # Средний similarity score
        avg_similarity = sum(r.similarity_score or 0.5 for r in results) / len(results)

        # Покрытие источников (сколько из активных источников дали результаты)
        source_coverage = len(sources_used) / len(active_sources) if active_sources else 0

        # Итоговый confidence: 70% similarity + 30% coverage
        confidence = (avg_similarity * 0.7) + (source_coverage * 0.3)

        return min(confidence, 1.0)


# Global instance
unified_search_service = UnifiedSearchService()
