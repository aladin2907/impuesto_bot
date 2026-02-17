"""
ToolExecutor - оркестратор выполнения инструментов агента

Определяет какие инструменты запускать на основе запроса и типа,
запускает их параллельно, собирает результаты.
"""
import asyncio
import logging
from typing import List, Optional

from app.models.agent import QueryType, ToolResult
from app.services.agent.tools import (
    TaxCalculator,
    CalendarLookup,
    DocumentSearch,
)

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Управляет выполнением инструментов агента

    Features:
    - Автоматическое определение нужных инструментов
    - Параллельное выполнение
    - Graceful degradation при ошибках
    """

    def __init__(self):
        # Инициализируем все инструменты
        self.tools = {
            'calculator': TaxCalculator(),
            'calendar': CalendarLookup(),
            'document': DocumentSearch(),
        }
        logger.info("ToolExecutor initialized with 3 tools")

    async def execute_tools(
        self,
        query: str,
        query_type: QueryType,
        enabled_tools: Optional[List[str]] = None
    ) -> List[ToolResult]:
        """
        Выполнить инструменты для данного запроса

        Args:
            query: Текст запроса пользователя
            query_type: Тип запроса (из классификатора)
            enabled_tools: Список разрешённых инструментов (None = все)

        Returns:
            List[ToolResult] - результаты выполнения инструментов
        """
        # Определяем какие инструменты запустить
        tools_to_run = []

        for tool_name, tool in self.tools.items():
            # Проверяем фильтр enabled_tools
            if enabled_tools and tool_name not in enabled_tools:
                continue

            # Спрашиваем у инструмента, нужно ли его запускать
            # query_type может быть как QueryType enum, так и строкой
            qt_value = query_type.value if hasattr(query_type, 'value') else query_type
            if tool.should_run(query, qt_value):
                tools_to_run.append((tool_name, tool))

        if not tools_to_run:
            logger.debug(f"No tools needed for query type {query_type}")
            return []

        logger.info(f"Running {len(tools_to_run)} tools: {[name for name, _ in tools_to_run]}")

        # Запускаем инструменты параллельно
        tasks = [
            self._execute_single_tool(tool_name, tool, query, query_type)
            for tool_name, tool in tools_to_run
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Фильтруем успешные результаты
        valid_results = []
        for result in results:
            if isinstance(result, ToolResult):
                valid_results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Tool execution failed: {result}")

        logger.info(
            f"Tools execution complete: {len(valid_results)} successful, "
            f"{len(results) - len(valid_results)} failed"
        )

        return valid_results

    async def _execute_single_tool(
        self,
        tool_name: str,
        tool,
        query: str,
        query_type: QueryType
    ) -> ToolResult:
        """Выполнить один инструмент с обработкой ошибок"""
        try:
            logger.debug(f"Executing tool: {tool_name}")
            result = await tool.execute(
                query=query,
                query_type=query_type
            )

            if result.success:
                logger.debug(
                    f"Tool {tool_name} succeeded in "
                    f"{result.execution_time_ms:.0f}ms"
                )
            else:
                logger.warning(f"Tool {tool_name} failed: {result.error}")

            return result

        except Exception as e:
            logger.error(f"Tool {tool_name} raised exception: {e}")
            # Возвращаем ToolResult с ошибкой
            return ToolResult(
                tool_type=tool.tool_type,
                success=False,
                error=f"Tool execution error: {str(e)}",
                execution_time_ms=0
            )

    async def execute_specific_tool(
        self,
        tool_name: str,
        **kwargs
    ) -> Optional[ToolResult]:
        """
        Выполнить конкретный инструмент по имени

        Args:
            tool_name: 'calculator', 'calendar', 'document'
            **kwargs: параметры для инструмента

        Returns:
            ToolResult или None если инструмент не найден
        """
        tool = self.tools.get(tool_name)
        if not tool:
            logger.warning(f"Tool {tool_name} not found")
            return None

        try:
            result = await tool.execute(**kwargs)
            return result
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}")
            return ToolResult(
                tool_type=tool.tool_type,
                success=False,
                error=str(e),
                execution_time_ms=0
            )
