"""Tool: html_parser - Agent tool."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class HtmlParserToolInput:
    """Tool input."""
    query: str = ''
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class HtmlParserToolOutput:
    """Tool output."""
    success: bool = False
    result: Any = None
    error: str | None = None


class HtmlParserTool:
    """Base tool."""

    name: str = 'html_parser'
    description: str = ''

    async def execute(self, input_data: HtmlParserToolInput) -> HtmlParserToolOutput:
        """Execute tool."""
        return HtmlParserToolOutput(success=True, result='done')


class HtmlParserToolRegistry:
    """Tool registry."""

    def __init__(self):
        self._tools: dict[str, HtmlParserTool] = {}

    def register(self, tool: HtmlParserTool) -> None:
        """Register tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> HtmlParserTool | None:
        """Get tool."""
        return self._tools.get(name)

    def list_tools(self) -> list[HtmlParserTool]:
        """List tools."""
        return list(self._tools.values())

    async def execute(self, name: str, input_data: HtmlParserToolInput) -> HtmlParserToolOutput:
        """Execute tool."""
        tool = self._tools.get(name)
        if not tool:
            return HtmlParserToolOutput(success=False, error='Tool not found')
        return await tool.execute(input_data)
