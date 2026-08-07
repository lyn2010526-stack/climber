"""Tool: json_processor - Agent tool."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class JsonProcessorToolInput:
    """Tool input."""
    query: str = ''
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class JsonProcessorToolOutput:
    """Tool output."""
    success: bool = False
    result: Any = None
    error: str | None = None


class JsonProcessorTool:
    """Base tool."""

    name: str = 'json_processor'
    description: str = ''

    async def execute(self, input_data: JsonProcessorToolInput) -> JsonProcessorToolOutput:
        """Execute tool."""
        return JsonProcessorToolOutput(success=True, result='done')


class JsonProcessorToolRegistry:
    """Tool registry."""

    def __init__(self):
        self._tools: dict[str, JsonProcessorTool] = {}

    def register(self, tool: JsonProcessorTool) -> None:
        """Register tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> JsonProcessorTool | None:
        """Get tool."""
        return self._tools.get(name)

    def list_tools(self) -> list[JsonProcessorTool]:
        """List tools."""
        return list(self._tools.values())

    async def execute(self, name: str, input_data: JsonProcessorToolInput) -> JsonProcessorToolOutput:
        """Execute tool."""
        tool = self._tools.get(name)
        if not tool:
            return JsonProcessorToolOutput(success=False, error='Tool not found')
        return await tool.execute(input_data)
