"""Tool: spreadsheet_reader - Agent tool."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SpreadsheetReaderToolInput:
    """Tool input."""
    query: str = ''
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class SpreadsheetReaderToolOutput:
    """Tool output."""
    success: bool = False
    result: Any = None
    error: str | None = None


class SpreadsheetReaderTool:
    """Base tool."""

    name: str = 'spreadsheet_reader'
    description: str = ''

    async def execute(self, input_data: SpreadsheetReaderToolInput) -> SpreadsheetReaderToolOutput:
        """Execute tool."""
        return SpreadsheetReaderToolOutput(success=True, result='done')


class SpreadsheetReaderToolRegistry:
    """Tool registry."""

    def __init__(self):
        self._tools: dict[str, SpreadsheetReaderTool] = {}

    def register(self, tool: SpreadsheetReaderTool) -> None:
        """Register tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> SpreadsheetReaderTool | None:
        """Get tool."""
        return self._tools.get(name)

    def list_tools(self) -> list[SpreadsheetReaderTool]:
        """List tools."""
        return list(self._tools.values())

    async def execute(self, name: str, input_data: SpreadsheetReaderToolInput) -> SpreadsheetReaderToolOutput:
        """Execute tool."""
        tool = self._tools.get(name)
        if not tool:
            return SpreadsheetReaderToolOutput(success=False, error='Tool not found')
        return await tool.execute(input_data)
