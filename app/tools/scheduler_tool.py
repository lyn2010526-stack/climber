"""Tool: scheduler - Agent tool."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SchedulerToolInput:
    """Tool input."""
    query: str = ''
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class SchedulerToolOutput:
    """Tool output."""
    success: bool = False
    result: Any = None
    error: str | None = None


class SchedulerTool:
    """Base tool."""

    name: str = 'scheduler'
    description: str = ''

    async def execute(self, input_data: SchedulerToolInput) -> SchedulerToolOutput:
        """Execute tool."""
        return SchedulerToolOutput(success=True, result='done')


class SchedulerToolRegistry:
    """Tool registry."""

    def __init__(self):
        self._tools: dict[str, SchedulerTool] = {}

    def register(self, tool: SchedulerTool) -> None:
        """Register tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> SchedulerTool | None:
        """Get tool."""
        return self._tools.get(name)

    def list_tools(self) -> list[SchedulerTool]:
        """List tools."""
        return list(self._tools.values())

    async def execute(self, name: str, input_data: SchedulerToolInput) -> SchedulerToolOutput:
        """Execute tool."""
        tool = self._tools.get(name)
        if not tool:
            return SchedulerToolOutput(success=False, error='Tool not found')
        return await tool.execute(input_data)
