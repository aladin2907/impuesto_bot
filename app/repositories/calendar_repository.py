"""
Репозиторий для работы с налоговым календарем
"""
from typing import List, Dict, Any, Optional
from datetime import date
from app.core.base_repository import BaseRepository


class CalendarRepository(BaseRepository):
    """Репозиторий для таблицы calendar_deadlines"""

    def __init__(self):
        super().__init__('calendar_deadlines')

    def get_upcoming_deadlines(
        self,
        start_date: date,
        end_date: date,
        applies_to: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Получение дедлайнов в указанном периоде

        Args:
            start_date: Начальная дата
            end_date: Конечная дата
            applies_to: Фильтр по категории (autonomos, empresas)

        Returns:
            Список дедлайнов
        """
        query = self.client.table(self.table_name)\
            .select('*')\
            .gte('deadline_date', start_date.isoformat())\
            .lte('deadline_date', end_date.isoformat())\
            .order('deadline_date')

        if applies_to:
            # Фильтрация по applies_to (array)
            query = query.contains('applies_to', applies_to)

        result = query.execute()
        return result.data if result.data else []

    def get_by_tax_model(self, tax_model: str) -> List[Dict[str, Any]]:
        """
        Получение дедлайнов по модели налога

        Args:
            tax_model: Модель налога (Modelo 303, Modelo 130, и т.д.)

        Returns:
            Список дедлайнов
        """
        result = self.client.table(self.table_name)\
            .select('*')\
            .eq('tax_model', tax_model)\
            .order('deadline_date')\
            .execute()

        return result.data if result.data else []

    async def search_by_query(
        self,
        query_text: str,
        limit: int = 10,
        tax_type: Optional[str] = None,
        applies_to: Optional[List[str]] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Keyword поиск по календарю (full-text search по description и tax_model)

        Args:
            query_text: Текст запроса
            limit: Количество результатов
            tax_type: Фильтр по типу налога (IVA, IRPF, etc.)
            applies_to: Фильтр по категории (autonomos, empresas)
            date_from: Начальная дата
            date_to: Конечная дата

        Returns:
            Список дедлайнов, отсортированных по релевантности и дате
        """
        try:
            # Используем .ilike() для case-insensitive поиска
            query = self.client.table(self.table_name)\
                .select('*')

            # Фильтры
            if tax_type:
                query = query.eq('tax_type', tax_type)

            if applies_to:
                query = query.contains('applies_to', applies_to)

            if date_from:
                query = query.gte('deadline_date', date_from.isoformat())

            if date_to:
                query = query.lte('deadline_date', date_to.isoformat())

            # Keyword search - ищем каждое значимое слово в одном OR
            if query_text:
                # Извлекаем значимые слова (>2 символов), убираем запятые
                words = [
                    w.strip('.,;:!?()') for w in query_text.split()
                    if len(w.strip('.,;:!?()')) > 2
                ]
                # Строим один or_ запрос со всеми словами по всем полям
                or_conditions = []
                for word in words[:5]:  # Макс 5 слов
                    pattern = f'%{word}%'
                    or_conditions.append(f'description.ilike.{pattern}')
                    or_conditions.append(f'tax_model.ilike.{pattern}')
                    or_conditions.append(f'tax_type.ilike.{pattern}')

                if or_conditions:
                    query = query.or_(','.join(or_conditions))

            query = query.order('deadline_date').limit(limit)

            result = query.execute()
            return result.data if result.data else []

        except Exception as e:
            print(f"⚠️ Ошибка при search_by_query в Calendar: {e}")
            # Fallback: просто возвращаем ближайшие дедлайны
            from datetime import date as date_type
            return self.get_upcoming_deadlines(
                start_date=date_from or date_type.today(),
                end_date=date_to or date_type(2026, 12, 31)
            )

    def get_next_deadline_for_model(self, tax_model: str) -> Optional[Dict[str, Any]]:
        """
        Получение следующего дедлайна для конкретной модели

        Args:
            tax_model: Модель налога (Modelo 303, Modelo 130, etc.)

        Returns:
            Ближайший дедлайн или None
        """
        today = date.today()

        result = self.client.table(self.table_name)\
            .select('*')\
            .eq('tax_model', tax_model)\
            .gte('deadline_date', today.isoformat())\
            .order('deadline_date')\
            .limit(1)\
            .execute()

        return result.data[0] if result.data else None
