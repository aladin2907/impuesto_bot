"""
QueryClassifier - классификация запросов пользователя через LLM

Определяет тип запроса для адаптивного поиска и генерации ответа.
Использует GPT-4o-mini для быстрой и дешевой классификации.
"""
import time
from typing import Optional

from app.models.agent import QueryType, ClassificationResult
from app.services.llm.llm_service import LLMService
from app.prompts import CLASSIFICATION_SYSTEM_PROMPT


class QueryClassifier:
    """
    Классификация запросов пользователя через LLM

    Использует GPT-4o-mini для быстрой классификации (0.2-0.5s).
    Поддерживает мультиязычные запросы (ES, RU, UK, EN).
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Args:
            llm_service: Сервис LLM для классификации.
                         Если None, создает свой instance с gpt-4o-mini.
        """
        if llm_service:
            self.llm_service = llm_service
        else:
            # Используем gpt-4.1-mini для классификации - быстрее и дешевле
            self.llm_service = LLMService(
                provider="openai",
                model="gpt-4.1-mini",
                temperature=0.0  # Детерминистическая классификация
            )
            self.llm_service.initialize()

    async def classify(self, query: str) -> ClassificationResult:
        """
        Классификация запроса пользователя

        Args:
            query: Текст запроса на любом языке

        Returns:
            ClassificationResult с типом запроса, confidence и временем
        """
        start_time = time.time()

        try:
            # Вызываем LLM для классификации
            response = await self.llm_service.generate_async(
                prompt=f"Clasifica esta consulta: {query}",
                system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
                max_tokens=20  # Нужен только один тип
            )

            # Парсим ответ
            raw_type = response.strip().lower().replace('"', '').replace("'", "")

            # Маппим на QueryType
            query_type = self._parse_query_type(raw_type)

            classification_time = (time.time() - start_time) * 1000

            return ClassificationResult(
                query_type=query_type,
                confidence=0.9 if query_type != QueryType.GENERAL_INFO else 0.7,
                reasoning=f"LLM classified as: {raw_type}",
                classification_time_ms=classification_time
            )

        except Exception as e:
            classification_time = (time.time() - start_time) * 1000
            print(f"⚠️ Classification error: {e}, falling back to GENERAL_INFO")

            return ClassificationResult(
                query_type=QueryType.GENERAL_INFO,
                confidence=0.5,
                reasoning=f"Error: {str(e)}, using fallback",
                classification_time_ms=classification_time
            )

    def _parse_query_type(self, raw_type: str) -> QueryType:
        """Парсинг ответа LLM в QueryType"""
        type_mapping = {
            "tax_calendar": QueryType.TAX_CALENDAR,
            "tax_calculation": QueryType.TAX_CALCULATION,
            "legal_interpretation": QueryType.LEGAL_INTERPRETATION,
            "practical_advice": QueryType.PRACTICAL_ADVICE,
            "news_update": QueryType.NEWS_UPDATE,
            "general_info": QueryType.GENERAL_INFO,
        }

        # Пробуем точное совпадение
        if raw_type in type_mapping:
            return type_mapping[raw_type]

        # Пробуем частичное совпадение
        for key, value in type_mapping.items():
            if key in raw_type:
                return value

        # Fallback
        return QueryType.GENERAL_INFO

    async def classify_with_translation(self, query: str) -> tuple[ClassificationResult, str]:
        """
        Классификация + перевод ключевых терминов на испанский

        Полезно для поиска по Calendar и PDF (данные на испанском).

        Args:
            query: Текст запроса

        Returns:
            Tuple[ClassificationResult, translated_query]
        """
        start_time = time.time()

        combined_prompt = f"""Analiza esta consulta fiscal y responde en formato:
TIPO: [una de: tax_calendar, tax_calculation, legal_interpretation, practical_advice, news_update, general_info]
KEYWORDS_ES: [palabras clave fiscales en español, separadas por comas]

Consulta: {query}"""

        try:
            response = await self.llm_service.generate_async(
                prompt=combined_prompt,
                system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
                max_tokens=100
            )

            lines = response.strip().split('\n')
            raw_type = "general_info"
            keywords_es = query  # Fallback - оригинальный запрос

            for line in lines:
                line = line.strip()
                if line.upper().startswith("TIPO:"):
                    raw_type = line.split(":", 1)[1].strip().lower()
                elif line.upper().startswith("KEYWORDS_ES:"):
                    keywords_es = line.split(":", 1)[1].strip()

            query_type = self._parse_query_type(raw_type)
            classification_time = (time.time() - start_time) * 1000

            classification = ClassificationResult(
                query_type=query_type,
                confidence=0.85,
                reasoning=f"Type: {raw_type}, Keywords: {keywords_es}",
                classification_time_ms=classification_time
            )

            return classification, keywords_es

        except Exception as e:
            classification_time = (time.time() - start_time) * 1000
            print(f"⚠️ classify_with_translation error: {e}")

            classification = ClassificationResult(
                query_type=QueryType.GENERAL_INFO,
                confidence=0.5,
                reasoning=f"Error: {str(e)}",
                classification_time_ms=classification_time
            )
            return classification, query
