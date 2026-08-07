"""Tool: csv_processor - Agent tool."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CsvProcessorToolInput:
    """Tool input."""
    query: str = ''
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class CsvProcessorToolOutput:
    """Tool output."""
    success: bool = False
    result: Any = None
    error: str | None = None


class CsvProcessorTool:
    """Base tool."""

    name: str = 'csv_processor'
    description: str = ''

    async def execute(self, input_data: CsvProcessorToolInput) -> CsvProcessorToolOutput:
        """Execute tool."""
        return CsvProcessorToolOutput(success=True, result='done')


class CsvProcessorToolRegistry:
    """Tool registry."""

    def __init__(self):
        self._tools: dict[str, CsvProcessorTool] = {}

    def register(self, tool: CsvProcessorTool) -> None:
        """Register tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> CsvProcessorTool | None:
        """Get tool."""
        return self._tools.get(name)

    def list_tools(self) -> list[CsvProcessorTool]:
        """List tools."""
        return list(self._tools.values())

    async def execute(self, name: str, input_data: CsvProcessorToolInput) -> CsvProcessorToolOutput:
        """Execute tool."""
        tool = self._tools.get(name)
        if not tool:
            return CsvProcessorToolOutput(success=False, error='Tool not found')
        return await tool.execute(input_data)
