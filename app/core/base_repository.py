"""
Базовый класс для работы с Supabase
"""
from typing import List, Dict, Any, Optional
from supabase import Client, create_client
from app.config.settings import Settings


class BaseRepository:
    """Базовый репозиторий для работы с таблицами Supabase"""

    def __init__(self, table_name: str):
        self.table_name = table_name
        self.settings = Settings()
        self.client: Client = self._init_client()

    def _init_client(self) -> Client:
        """Инициализация Supabase клиента"""
        return create_client(
            self.settings.SUPABASE_URL,
            self.settings.SUPABASE_KEY
        )

    def insert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Вставка одной записи"""
        result = self.client.table(self.table_name).insert(data).execute()
        return result.data[0] if result.data else None

    def insert_many(self, data: List[Dict[str, Any]], batch_size: int = 100) -> int:
        """
        Вставка множества записей батчами

        Args:
            data: Список записей для вставки
            batch_size: Размер батча (по умолчанию 100)

        Returns:
            Количество вставленных записей
        """
        total_inserted = 0

        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            try:
                result = self.client.table(self.table_name).insert(batch).execute()
                total_inserted += len(result.data) if result.data else 0
                print(f"✅ Вставлено {len(result.data)} записей (батч {i//batch_size + 1})")
            except Exception as e:
                print(f"❌ Ошибка при вставке батча {i//batch_size + 1}: {e}")
                continue

        return total_inserted

    def select_all(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Получение всех записей"""
        query = self.client.table(self.table_name).select('*')

        if limit:
            query = query.limit(limit)

        result = query.execute()
        return result.data if result.data else []

    def select_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Получение записи по ID"""
        result = self.client.table(self.table_name).select('*').eq('id', record_id).execute()
        return result.data[0] if result.data else None

    def count(self) -> int:
        """Подсчет количества записей в таблице"""
        result = self.client.table(self.table_name).select('id', count='exact').limit(0).execute()
        return result.count or 0

    def delete_all(self) -> int:
        """
        ОСТОРОЖНО: Удаление всех записей из таблицы
        Используйте только для очистки при миграции
        """
        # Supabase не поддерживает удаление всех записей одной командой
        # Поэтому сначала получаем все ID
        records = self.select_all()
        deleted_count = 0

        for record in records:
            try:
                self.client.table(self.table_name).delete().eq('id', record['id']).execute()
                deleted_count += 1
            except Exception as e:
                print(f"⚠️ Ошибка при удалении записи {record['id']}: {e}")

        return deleted_count

    def upsert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Вставка или обновление записи"""
        result = self.client.table(self.table_name).upsert(data).execute()
        return result.data[0] if result.data else None
