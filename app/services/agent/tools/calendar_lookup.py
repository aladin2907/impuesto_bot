"""
CalendarLookup - инструмент для поиска налоговых дедлайнов

Работает с CalendarRepository (Supabase таблица calendar_deadlines)
"""
import re
import time
from datetime import date, timedelta
from typing import Optional, List, Dict, Any
from app.models.agent import ToolType, ToolResult, QueryType
from app.services.agent.tools.base_tool import BaseTool
from app.repositories.calendar_repository import CalendarRepository


# Маппинг моделей
TAX_MODELS = {
    '303': 'Modelo 303',
    '130': 'Modelo 130',
    '111': 'Modelo 111',
    '115': 'Modelo 115',
    '349': 'Modelo 349',
    '390': 'Modelo 390',
    '190': 'Modelo 190',
    '347': 'Modelo 347',
    '100': 'Modelo 100',
    '200': 'Modelo 200',
    '714': 'Modelo 714',
    '720': 'Modelo 720',
}

# Квартальные маппинги
QUARTER_MONTHS = {
    'Q1': (1, 3), 'Q2': (4, 6), 'Q3': (7, 9), 'Q4': (10, 12),
    '1': (1, 3), '2': (4, 6), '3': (7, 9), '4': (10, 12),
    'primer': (1, 3), 'segundo': (4, 6), 'tercer': (7, 9), 'cuarto': (10, 12),
    'первый': (1, 3), 'второй': (4, 6), 'третий': (7, 9), 'четвёртый': (10, 12),
    'первого': (1, 3), 'второго': (4, 6), 'третьего': (7, 9), 'четвёртого': (10, 12),
}


class CalendarLookup(BaseTool):
    """Инструмент для поиска налоговых дедлайнов"""

    def __init__(self):
        super().__init__(ToolType.CALENDAR_LOOKUP)
        self.repo = CalendarRepository()

    def should_run(self, query: str, query_type: str) -> bool:
        """Запускать для запросов о сроках и дедлайнах"""
        if query_type == QueryType.TAX_CALENDAR:
            return True

        q = query.lower()
        calendar_keywords = [
            'plazo', 'fecha', 'vencimiento', 'presentar', 'declaración',
            'trimestre', 'cuándo', 'cuando', 'deadline', 'calendario',
            'срок', 'дедлайн', 'подавать', 'подать', 'когда', 'квартал',
            'modelo 3', 'modelo 1', 'modelo 2',
        ]
        return any(kw in q for kw in calendar_keywords)

    async def execute(self, **kwargs) -> ToolResult:
        """Поиск дедлайнов"""
        start = time.time()
        query = kwargs.get('query', '')

        try:
            q = query.lower()

            # 1. Ищем конкретную модель
            model = self._extract_model(q)
            if model:
                result = self._lookup_by_model(model)
                if result:
                    return self._success(result, (time.time() - start) * 1000)

            # 2. Ищем квартал
            quarter = self._extract_quarter(q)
            if quarter:
                result = self._lookup_by_quarter(quarter)
                if result:
                    return self._success(result, (time.time() - start) * 1000)

            # 3. По умолчанию - ближайшие дедлайны
            result = self._get_upcoming()
            return self._success(result, (time.time() - start) * 1000)

        except Exception as e:
            return self._error(str(e), (time.time() - start) * 1000)

    def _extract_model(self, query: str) -> Optional[str]:
        """Извлечь номер модели из запроса"""
        # "modelo 303", "model 303", "модель 303", просто "303"
        match = re.search(r'(?:modelo?|модел[ьи])\s*(\d{3})', query, re.IGNORECASE)
        if match:
            num = match.group(1)
            return TAX_MODELS.get(num, f'Modelo {num}')

        # Ищем по типу налога
        if 'iva' in query or 'ива' in query or 'ндс' in query:
            return 'Modelo 303'
        if 'irpf' in query and ('autónom' in query or 'autonom' in query or 'автоном' in query):
            return 'Modelo 130'
        if 'retención' in query or 'retencion' in query or 'retenciones' in query:
            return 'Modelo 111'

        return None

    def _extract_quarter(self, query: str) -> Optional[str]:
        """Извлечь квартал из запроса"""
        # "tercer trimestre", "Q3", "3 trimestre", "третий квартал"
        for key, months in QUARTER_MONTHS.items():
            if key in query:
                # Определяем Q
                q_num = {(1, 3): 'Q1', (4, 6): 'Q2', (7, 9): 'Q3', (10, 12): 'Q4'}
                return q_num.get(months, 'Q1')

        match = re.search(r'[qQкК](\d)', query)
        if match:
            return f'Q{match.group(1)}'

        return None

    def _lookup_by_model(self, tax_model: str) -> str:
        """Поиск дедлайнов по модели налога"""
        deadlines = self.repo.get_by_tax_model(tax_model)

        if not deadlines:
            return f"No he encontrado plazos para {tax_model} en el calendario."

        today = date.today()
        upcoming = [d for d in deadlines if d.get('deadline_date', '') >= today.isoformat()]
        past = [d for d in deadlines if d.get('deadline_date', '') < today.isoformat()]

        lines = [f"**Plazos para {tax_model}:**", ""]

        if upcoming:
            lines.append("**Próximos vencimientos:**")
            for d in upcoming[:5]:
                deadline_date = d.get('deadline_date', 'N/A')
                desc = d.get('description', '')
                quarter = d.get('quarter', '')
                applies = ', '.join(d.get('applies_to', []))
                lines.append(
                    f"  - **{deadline_date}** ({quarter}): {desc}"
                    + (f" | Aplica a: {applies}" if applies else "")
                )
        else:
            lines.append("_No hay plazos futuros registrados para este modelo._")

        if past:
            lines.append("")
            lines.append("**Últimos plazos pasados:**")
            for d in past[-3:]:
                deadline_date = d.get('deadline_date', 'N/A')
                desc = d.get('description', '')
                quarter = d.get('quarter', '')
                lines.append(f"  - ~~{deadline_date}~~ ({quarter}): {desc}")

        return "\n".join(lines)

    def _lookup_by_quarter(self, quarter: str) -> str:
        """Поиск дедлайнов по кварталу"""
        today = date.today()
        year = today.year

        # Определяем месяцы квартала
        q_map = {'Q1': (1, 3), 'Q2': (4, 6), 'Q3': (7, 9), 'Q4': (10, 12)}
        start_month, end_month = q_map.get(quarter, (1, 3))

        start_date = date(year, start_month, 1)
        # Дедлайны обычно в следующем месяце после квартала
        end_date = date(year, min(end_month + 2, 12), 28)

        deadlines = self.repo.get_upcoming_deadlines(start_date, end_date)

        if not deadlines:
            return f"No he encontrado plazos para {quarter} {year} en el calendario."

        # Фильтруем по кварталу
        q_deadlines = [d for d in deadlines if d.get('quarter') == quarter]
        if not q_deadlines:
            q_deadlines = deadlines

        lines = [f"**Plazos del {quarter} {year}:**", ""]

        for d in q_deadlines:
            deadline_date = d.get('deadline_date', 'N/A')
            model = d.get('tax_model', '')
            desc = d.get('description', '')
            tax_type = d.get('tax_type', '')
            applies = ', '.join(d.get('applies_to', []))

            status = ""
            if deadline_date < today.isoformat():
                status = " ~~(pasado)~~"
            elif deadline_date <= (today + timedelta(days=7)).isoformat():
                status = " ⚠️ **¡Próximo!**"

            lines.append(
                f"  - **{deadline_date}** - {model} ({tax_type}): {desc}{status}"
                + (f"\n    Aplica a: {applies}" if applies else "")
            )

        return "\n".join(lines)

    def _get_upcoming(self) -> str:
        """Получить ближайшие дедлайны"""
        today = date.today()
        end = today + timedelta(days=90)

        deadlines = self.repo.get_upcoming_deadlines(today, end)

        if not deadlines:
            return "No he encontrado plazos próximos en los próximos 90 días."

        lines = ["**Próximos vencimientos fiscales:**", ""]

        for d in deadlines[:10]:
            deadline_date = d.get('deadline_date', 'N/A')
            model = d.get('tax_model', '')
            desc = d.get('description', '')
            tax_type = d.get('tax_type', '')
            applies = ', '.join(d.get('applies_to', []))

            days_left = (date.fromisoformat(deadline_date) - today).days
            urgency = ""
            if days_left <= 7:
                urgency = " ⚠️"
            elif days_left <= 14:
                urgency = " ⏰"

            lines.append(
                f"  - **{deadline_date}** (en {days_left} días{urgency}) - "
                f"{model} ({tax_type}): {desc}"
                + (f"\n    Aplica a: {applies}" if applies else "")
            )

        return "\n".join(lines)
