"""Tool: code_parser - Agent tool."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CodeParserToolInput:
    """Tool input."""
    query: str = ''
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeParserToolOutput:
    """Tool output."""
    success: bool = False
    result: Any = None
    error: str | None = None


class CodeParserTool:
    """Base tool."""

    name: str = 'code_parser'
    description: str = ''

    async def execute(self, input_data: CodeParserToolInput) -> CodeParserToolOutput:
        """Execute tool."""
        return CodeParserToolOutput(success=True, result='done')


class CodeParserToolRegistry:
    """Tool registry."""

    def __init__(self):
        self._tools: dict[str, CodeParserTool] = {}

    def register(self, tool: CodeParserTool) -> None:
        """Register tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> CodeParserTool | None:
        """Get tool."""
        return self._tools.get(name)

    def list_tools(self) -> list[CodeParserTool]:
        """List tools."""
        return list(self._tools.values())

    async def execute(self, name: str, input_data: CodeParserToolInput) -> CodeParserToolOutput:
        """Execute tool."""
        tool = self._tools.get(name)
        if not tool:
            return CodeParserToolOutput(success=False, error='Tool not found')
        return await tool.execute(input_data)
