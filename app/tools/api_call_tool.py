"""Tool: api_call - Agent tool."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ApiCallToolInput:
    """Tool input."""
    query: str = ''
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class ApiCallToolOutput:
    """Tool output."""
    success: bool = False
    result: Any = None
    error: str | None = None


class ApiCallTool:
    """Base tool."""

    name: str = 'api_call'
    description: str = ''

    async def execute(self, input_data: ApiCallToolInput) -> ApiCallToolOutput:
        """Execute tool."""
        return ApiCallToolOutput(success=True, result='done')


class ApiCallToolRegistry:
    """Tool registry."""

    def __init__(self):
        self._tools: dict[str, ApiCallTool] = {}

    def register(self, tool: ApiCallTool) -> None:
        """Register tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> ApiCallTool | None:
        """Get tool."""
        return self._tools.get(name)

    def list_tools(self) -> list[ApiCallTool]:
        """List tools."""
        return list(self._tools.values())

    async def execute(self, name: str, input_data: ApiCallToolInput) -> ApiCallToolOutput:
        """Execute tool."""
        tool = self._tools.get(name)
        if not tool:
            return ApiCallToolOutput(success=False, error='Tool not found')
        return await tool.execute(input_data)
