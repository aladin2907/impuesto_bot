"""
Репозиторий для работы с PDF документами
"""
from typing import List, Dict, Any, Optional
from app.core.base_repository import BaseRepository


class PDFRepository(BaseRepository):
    """Репозиторий для таблицы pdf_documents_content"""

    def __init__(self):
        super().__init__('pdf_documents_content')

    async def hybrid_search(
        self,
        query_text: str,
        query_embedding: List[float],
        limit: int = 10,
        similarity_threshold: float = 0.5,
        document_type: Optional[str] = None,
        region: Optional[str] = None,
        categories: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Гибридный поиск (kNN + BM25) по PDF документам через RPC функцию

        Args:
            query_text: Текст запроса для keyword поиска
            query_embedding: Вектор запроса для semantic поиска (1536d)
            limit: Количество результатов
            similarity_threshold: Порог схожести (0.0-1.0)
            document_type: Фильтр по типу документа (law, regulation, guide, form)
            region: Фильтр по региону (national, valencia, madrid, etc.)
            categories: Фильтр по категориям (irpf, iva, etc.)

        Returns:
            Список результатов с полями: id, document_title, content,
            chunk_number, similarity, rank, document_type, region, categories
        """
        try:
            # Вызов RPC функции search_pdf_hybrid
            params = {
                'query_text': query_text,
                'query_embedding': query_embedding,
                'match_limit': limit,
                'similarity_threshold': similarity_threshold
            }

            # Добавляем опциональные фильтры
            if document_type:
                params['filter_document_type'] = document_type
            if region:
                params['filter_region'] = region
            if categories:
                params['filter_categories'] = categories

            result = self.client.rpc('search_pdf_hybrid', params).execute()
            return result.data if result.data else []

        except Exception as e:
            print(f"⚠️ Ошибка при hybrid search в PDF: {e}")
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
            # Простой векторный поиск через match_documents (если есть)
            result = self.client.rpc('match_documents', {
                'query_embedding': query_embedding,
                'match_count': limit
            }).execute()

            return result.data if result.data else []
        except Exception as e:
            print(f"⚠️ Fallback vector search также не сработал: {e}")
            return []

    def get_by_document_title(self, document_title: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Получение всех чанков документа по названию

        Args:
            document_title: Название документа
            limit: Лимит результатов

        Returns:
            Список чанков документа
        """
        query = self.client.table(self.table_name)\
            .select('*')\
            .eq('document_title', document_title)\
            .order('chunk_number')

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
        Получение документов по категории

        Args:
            category: Категория (irpf, iva, sociedades, etc.)
            limit: Лимит результатов

        Returns:
            Список документов
        """
        query = self.client.table(self.table_name)\
            .select('*')\
            .contains('categories', [category])\
            .order('document_title')

        if limit:
            query = query.limit(limit)

        result = query.execute()
        return result.data if result.data else []

    def get_by_region(
        self,
        region: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Получение документов по региону

        Args:
            region: Регион (national, valencia, madrid, etc.)
            limit: Лимит результатов

        Returns:
            Список документов
        """
        query = self.client.table(self.table_name)\
            .select('*')\
            .eq('region', region)\
            .order('document_title')

        if limit:
            query = query.limit(limit)

        result = query.execute()
        return result.data if result.data else []
