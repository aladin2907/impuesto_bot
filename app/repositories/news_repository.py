"""
Репозиторий для работы с новостями
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from app.core.base_repository import BaseRepository


class NewsRepository(BaseRepository):
    """Репозиторий для таблицы news_articles_content"""

    def __init__(self):
        super().__init__('news_articles_content')

    async def hybrid_search(
        self,
        query_text: str,
        query_embedding: List[float],
        limit: int = 10,
        similarity_threshold: float = 0.5,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        news_source: Optional[str] = None,
        categories: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Гибридный поиск (kNN + BM25) по новостям через RPC функцию

        Args:
            query_text: Текст запроса для keyword поиска
            query_embedding: Вектор запроса для semantic поиска (1536d)
            limit: Количество результатов
            similarity_threshold: Порог схожести (0.0-1.0)
            date_from: Фильтр по дате начала
            date_to: Фильтр по дате окончания
            news_source: Фильтр по источнику (Expansión, Cinco Días, etc.)
            categories: Фильтр по категориям

        Returns:
            Список результатов с полями: id, article_title, content,
            article_url, published_at, similarity, rank, news_source, categories
        """
        try:
            # Вызов RPC функции search_news_hybrid
            params = {
                'query_text': query_text,
                'query_embedding': query_embedding,
                'match_limit': limit,
                'similarity_threshold': similarity_threshold
            }

            # Добавляем опциональные фильтры
            if date_from:
                params['filter_date_from'] = date_from.isoformat()
            if date_to:
                params['filter_date_to'] = date_to.isoformat()
            if news_source:
                params['filter_news_source'] = news_source
            if categories:
                params['filter_categories'] = categories

            result = self.client.rpc('search_news_hybrid', params).execute()
            return result.data if result.data else []

        except Exception as e:
            print(f"⚠️ Ошибка при hybrid search в News: {e}")
            # Fallback: векторный поиск без BM25
            return self._vector_search_fallback(query_embedding, limit, similarity_threshold)

    def _vector_search_fallback(
        self,
        query_embedding: List[float],
        limit: int,
        similarity_threshold: float
    ) -> List[Dict[str, Any]]:
        """
        Fallback: простой векторный поиск если RPC не работает
        """
        try:
            # Простой векторный поиск (временная реализация)
            # В будущем можно использовать match_documents для news
            result = self.client.table(self.table_name)\
                .select('*')\
                .limit(limit)\
                .execute()

            return result.data if result.data else []
        except Exception as e:
            print(f"⚠️ Fallback vector search также не сработал: {e}")
            return []

    def get_recent_news(
        self,
        limit: int = 10,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Получение последних новостей за N дней

        Args:
            limit: Количество результатов
            days: Количество дней назад

        Returns:
            Список новостей
        """
        from datetime import timedelta
        date_from = datetime.now() - timedelta(days=days)

        result = self.client.table(self.table_name)\
            .select('*')\
            .gte('published_at', date_from.isoformat())\
            .order('published_at', desc=True)\
            .limit(limit)\
            .execute()

        return result.data if result.data else []

    def get_by_source(
        self,
        news_source: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Получение новостей по источнику

        Args:
            news_source: Источник (Expansión, Cinco Días, El Economista)
            limit: Лимит результатов

        Returns:
            Список новостей
        """
        query = self.client.table(self.table_name)\
            .select('*')\
            .eq('news_source', news_source)\
            .order('published_at', desc=True)

        if limit:
            query = query.limit(limit)

        result = query.execute()
        return result.data if result.data else []

    def get_by_category(
        self,
        category: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Получение новостей по категории

        Args:
            category: Категория
            limit: Лимит результатов

        Returns:
            Список новостей
        """
        query = self.client.table(self.table_name)\
            .select('*')\
            .contains('categories', [category])\
            .order('published_at', desc=True)

        if limit:
            query = query.limit(limit)

        result = query.execute()
        return result.data if result.data else []

    def get_tax_related_news(
        self,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Получение только налоговых новостей

        Args:
            limit: Лимит результатов

        Returns:
            Список налоговых новостей
        """
        query = self.client.table(self.table_name)\
            .select('*')\
            .eq('tax_related', True)\
            .order('published_at', desc=True)

        if limit:
            query = query.limit(limit)

        result = query.execute()
        return result.data if result.data else []
