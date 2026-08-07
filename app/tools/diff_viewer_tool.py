"""Tool: diff_viewer - Agent tool."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiffViewerToolInput:
    """Tool input."""
    query: str = ''
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class DiffViewerToolOutput:
    """Tool output."""
    success: bool = False
    result: Any = None
    error: str | None = None


class DiffViewerTool:
    """Base tool."""

    name: str = 'diff_viewer'
    description: str = ''

    async def execute(self, input_data: DiffViewerToolInput) -> DiffViewerToolOutput:
        """Execute tool."""
        return DiffViewerToolOutput(success=True, result='done')


class DiffViewerToolRegistry:
    """Tool registry."""

    def __init__(self):
        self._tools: dict[str, DiffViewerTool] = {}

    def register(self, tool: DiffViewerTool) -> None:
        """Register tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> DiffViewerTool | None:
        """Get tool."""
        return self._tools.get(name)

    def list_tools(self) -> list[DiffViewerTool]:
        """List tools."""
        return list(self._tools.values())

    async def execute(self, name: str, input_data: DiffViewerToolInput) -> DiffViewerToolOutput:
        """Execute tool."""
        tool = self._tools.get(name)
        if not tool:
            return DiffViewerToolOutput(success=False, error='Tool not found')
        return await tool.execute(input_data)
