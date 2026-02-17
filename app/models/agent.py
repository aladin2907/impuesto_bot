"""
Модели данных для AI Tax Agent
"""
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class QueryType(str, Enum):
    """Типы запросов для классификации"""
    TAX_CALENDAR = "tax_calendar"  # Вопросы о сроках и дедлайнах
    TAX_CALCULATION = "tax_calculation"  # Расчеты налогов и сборов
    LEGAL_INTERPRETATION = "legal_interpretation"  # Толкование законов и норм
    PRACTICAL_ADVICE = "practical_advice"  # Практические советы и рекомендации
    NEWS_UPDATE = "news_update"  # Актуальные новости и изменения
    GENERAL_INFO = "general_info"  # Общая информация о налогах


class SearchSource(str, Enum):
    """Источники данных для поиска"""
    TELEGRAM = "telegram"
    PDF = "pdf"
    CALENDAR = "calendar"
    NEWS = "news"


class SearchResult(BaseModel):
    """Результат поиска из одного источника"""
    source: SearchSource
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    similarity_score: Optional[float] = None
    relevance_score: Optional[float] = None

    class Config:
        use_enum_values = True


class Context(BaseModel):
    """Контекст для генерации ответа"""
    results: List[SearchResult]
    sources_used: List[SearchSource]
    confidence_score: float = Field(ge=0.0, le=1.0)
    total_results: int

    class Config:
        use_enum_values = True


class ToolType(str, Enum):
    """Типы инструментов агента"""
    TAX_CALCULATOR = "tax_calculator"
    CALENDAR_LOOKUP = "calendar_lookup"
    DOCUMENT_SEARCH = "document_search"
    WEB_SEARCH = "web_search"


class ToolResult(BaseModel):
    """Результат выполнения инструмента"""
    tool_type: ToolType
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None

    class Config:
        use_enum_values = True


class AgentResponse(BaseModel):
    """Финальный ответ агента"""
    text: str
    query_type: QueryType
    context: Context
    tools_used: List[ToolResult] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    processing_time_ms: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class UserProfile(BaseModel):
    """Профиль пользователя для персонализации"""
    user_type: Optional[str] = None  # autonomo, empresa, etc.
    region: Optional[str] = None  # valencia, madrid, etc.
    tax_models: List[str] = Field(default_factory=list)  # [303, 130, etc.]
    preferred_language: str = "es"


class AgentRequest(BaseModel):
    """Запрос к агенту"""
    query: str = Field(min_length=1, max_length=2000)
    user_id: str
    session_id: Optional[str] = None
    user_profile: Optional[UserProfile] = None
    include_tools: bool = True
    max_context_items: int = Field(default=10, ge=1, le=20)


class ClassificationResult(BaseModel):
    """Результат классификации запроса"""
    query_type: QueryType
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str] = None
    classification_time_ms: float

    class Config:
        use_enum_values = True


# Source weights for different query types
SOURCE_WEIGHTS: Dict[QueryType, Dict[SearchSource, float]] = {
    QueryType.TAX_CALENDAR: {
        SearchSource.CALENDAR: 0.7,
        SearchSource.TELEGRAM: 0.2,
        SearchSource.PDF: 0.1,
        SearchSource.NEWS: 0.0
    },
    QueryType.TAX_CALCULATION: {
        SearchSource.PDF: 0.4,
        SearchSource.TELEGRAM: 0.3,
        SearchSource.CALENDAR: 0.2,
        SearchSource.NEWS: 0.1
    },
    QueryType.LEGAL_INTERPRETATION: {
        SearchSource.PDF: 0.6,
        SearchSource.TELEGRAM: 0.2,
        SearchSource.CALENDAR: 0.1,
        SearchSource.NEWS: 0.1
    },
    QueryType.PRACTICAL_ADVICE: {
        SearchSource.TELEGRAM: 0.5,
        SearchSource.PDF: 0.2,
        SearchSource.CALENDAR: 0.2,
        SearchSource.NEWS: 0.1
    },
    QueryType.NEWS_UPDATE: {
        SearchSource.NEWS: 0.5,
        SearchSource.TELEGRAM: 0.3,
        SearchSource.PDF: 0.1,
        SearchSource.CALENDAR: 0.1
    },
    QueryType.GENERAL_INFO: {
        SearchSource.TELEGRAM: 0.3,
        SearchSource.PDF: 0.3,
        SearchSource.CALENDAR: 0.2,
        SearchSource.NEWS: 0.2
    }
}
