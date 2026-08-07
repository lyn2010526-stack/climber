"""Tool: chart_generator - Agent tool."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChartGeneratorToolInput:
    """Tool input."""
    query: str = ''
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChartGeneratorToolOutput:
    """Tool output."""
    success: bool = False
    result: Any = None
    error: str | None = None


class ChartGeneratorTool:
    """Base tool."""

    name: str = 'chart_generator'
    description: str = ''

    async def execute(self, input_data: ChartGeneratorToolInput) -> ChartGeneratorToolOutput:
        """Execute tool."""
        return ChartGeneratorToolOutput(success=True, result='done')


class ChartGeneratorToolRegistry:
    """Tool registry."""

    def __init__(self):
        self._tools: dict[str, ChartGeneratorTool] = {}

    def register(self, tool: ChartGeneratorTool) -> None:
        """Register tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> ChartGeneratorTool | None:
        """Get tool."""
        return self._tools.get(name)

    def list_tools(self) -> list[ChartGeneratorTool]:
        """List tools."""
        return list(self._tools.values())

    async def execute(self, name: str, input_data: ChartGeneratorToolInput) -> ChartGeneratorToolOutput:
        """Execute tool."""
        tool = self._tools.get(name)
        if not tool:
            return ChartGeneratorToolOutput(success=False, error='Tool not found')
        return await tool.execute(input_data)
