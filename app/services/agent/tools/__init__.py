"""
Agent Tools - инструменты для расширения возможностей агента
"""
from app.services.agent.tools.base_tool import BaseTool
from app.services.agent.tools.tax_calculator import TaxCalculator
from app.services.agent.tools.calendar_lookup import CalendarLookup
from app.services.agent.tools.document_search import DocumentSearch

__all__ = [
    'BaseTool',
    'TaxCalculator',
    'CalendarLookup',
    'DocumentSearch',
]
