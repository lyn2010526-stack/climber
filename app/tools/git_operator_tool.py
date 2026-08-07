"""Tool: git_operator - Agent tool."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GitOperatorToolInput:
    """Tool input."""
    query: str = ''
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class GitOperatorToolOutput:
    """Tool output."""
    success: bool = False
    result: Any = None
    error: str | None = None


class GitOperatorTool:
    """Base tool."""

    name: str = 'git_operator'
    description: str = ''

    async def execute(self, input_data: GitOperatorToolInput) -> GitOperatorToolOutput:
        """Execute tool."""
        return GitOperatorToolOutput(success=True, result='done')


class GitOperatorToolRegistry:
    """Tool registry."""

    def __init__(self):
        self._tools: dict[str, GitOperatorTool] = {}

    def register(self, tool: GitOperatorTool) -> None:
        """Register tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> GitOperatorTool | None:
        """Get tool."""
        return self._tools.get(name)

    def list_tools(self) -> list[GitOperatorTool]:
        """List tools."""
        return list(self._tools.values())

    async def execute(self, name: str, input_data: GitOperatorToolInput) -> GitOperatorToolOutput:
        """Execute tool."""
        tool = self._tools.get(name)
        if not tool:
            return GitOperatorToolOutput(success=False, error='Tool not found')
        return await tool.execute(input_data)
