"""
Репозиторий для работы с Telegram тредами
"""
from typing import List, Dict, Any, Optional
from app.core.base_repository import BaseRepository


class TelegramRepository(BaseRepository):
    """Репозиторий для таблицы telegram_threads_content"""

    def __init__(self):
        super().__init__('telegram_threads_content')

    async def hybrid_search(
        self,
        query_text: str,
        query_embedding: List[float],
        limit: int = 10,
        similarity_threshold: float = 0.5,
        group_name: Optional[str] = None,
        quality_score_min: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Гибридный поиск (kNN + BM25) по Telegram тредам через RPC функцию

        Args:
            query_text: Текст запроса для keyword поиска
            query_embedding: Вектор запроса для semantic поиска (1024d)
            limit: Количество результатов
            similarity_threshold: Порог схожести (0.0-1.0)
            group_name: Фильтр по группе (IT Autonomos Spain, Chat for Nomads)
            quality_score_min: Минимальный порог качества

        Returns:
            Список результатов с полями: id, thread_id, group_name, content,
            similarity, rank, quality_score, message_count
        """
        try:
            # Вызов RPC функции search_telegram_hybrid
            params = {
                'query_text': query_text,
                'query_embedding': query_embedding,
                'match_limit': limit,
                'similarity_threshold': similarity_threshold
            }

            # Добавляем опциональные фильтры
            if group_name:
                params['filter_group_name'] = group_name
            if quality_score_min:
                params['filter_quality_min'] = quality_score_min

            result = self.client.rpc('search_telegram_hybrid', params).execute()
            return result.data if result.data else []

        except Exception as e:
            print(f"⚠️ Ошибка при hybrid search в Telegram: {e}")
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
            # Используем match_documents если hybrid search не работает
            result = self.client.rpc('match_documents', {
                'query_embedding': query_embedding,
                'match_count': limit
            }).execute()

            return result.data if result.data else []
        except Exception as e:
            print(f"⚠️ Fallback vector search также не сработал: {e}")
            return []

    def get_by_group(self, group_name: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Получение тредов по группе

        Args:
            group_name: Название группы
            limit: Лимит результатов

        Returns:
            Список тредов
        """
        query = self.client.table(self.table_name)\
            .select('*')\
            .eq('group_name', group_name)\
            .order('first_message_date', desc=True)

        if limit:
            query = query.limit(limit)

        result = query.execute()
        return result.data if result.data else []

    def get_by_thread_id(self, thread_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение треда по thread_id

        Args:
            thread_id: ID треда в Telegram

        Returns:
            Данные треда или None
        """
        result = self.client.table(self.table_name)\
            .select('*')\
            .eq('thread_id', thread_id)\
            .execute()

        return result.data[0] if result.data else None
