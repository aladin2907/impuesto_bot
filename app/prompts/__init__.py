"""
Prompts package - все промпты AI налогового консультанта
"""
from app.prompts.base_system import BASE_SYSTEM_PROMPT
from app.prompts.tax_calendar import TAX_CALENDAR_PROMPT
from app.prompts.tax_calculation import TAX_CALCULATION_PROMPT
from app.prompts.legal_interpretation import LEGAL_INTERPRETATION_PROMPT
from app.prompts.practical_advice import PRACTICAL_ADVICE_PROMPT
from app.prompts.news_update import NEWS_UPDATE_PROMPT
from app.prompts.general_info import GENERAL_INFO_PROMPT
from app.prompts.classifier import CLASSIFICATION_SYSTEM_PROMPT
from app.prompts.bot_messages import (
    START_MESSAGE,
    HELP_MESSAGE,
    ABOUT_MESSAGE,
    CALENDAR_INTRO_MESSAGE,
    LOW_CONFIDENCE_WARNING_ES,
    LOW_CONFIDENCE_WARNING_RU
)

__all__ = [
    'BASE_SYSTEM_PROMPT',
    'TAX_CALENDAR_PROMPT',
    'TAX_CALCULATION_PROMPT',
    'LEGAL_INTERPRETATION_PROMPT',
    'PRACTICAL_ADVICE_PROMPT',
    'NEWS_UPDATE_PROMPT',
    'GENERAL_INFO_PROMPT',
    'CLASSIFICATION_SYSTEM_PROMPT',
    'START_MESSAGE',
    'HELP_MESSAGE',
    'ABOUT_MESSAGE',
    'CALENDAR_INTRO_MESSAGE',
    'LOW_CONFIDENCE_WARNING_ES',
    'LOW_CONFIDENCE_WARNING_RU',
]
