"""
BaseTool - интерфейс для инструментов агента
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from app.models.agent import ToolType, ToolResult


class BaseTool(ABC):
    """Базовый класс для всех инструментов агента"""

    def __init__(self, tool_type: ToolType):
        self.tool_type = tool_type

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Выполнить инструмент"""
        pass

    @abstractmethod
    def should_run(self, query: str, query_type: str) -> bool:
        """Определить, нужно ли запускать этот инструмент для данного запроса"""
        pass

    def _success(self, result: Any, execution_time_ms: float = 0) -> ToolResult:
        return ToolResult(
            tool_type=self.tool_type,
            success=True,
            result=result,
            execution_time_ms=execution_time_ms
        )

    def _error(self, error: str, execution_time_ms: float = 0) -> ToolResult:
        return ToolResult(
            tool_type=self.tool_type,
            success=False,
            error=error,
            execution_time_ms=execution_time_ms
        )
