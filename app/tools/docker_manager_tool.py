"""Tool: docker_manager - Agent tool."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DockerManagerToolInput:
    """Tool input."""
    query: str = ''
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class DockerManagerToolOutput:
    """Tool output."""
    success: bool = False
    result: Any = None
    error: str | None = None


class DockerManagerTool:
    """Base tool."""

    name: str = 'docker_manager'
    description: str = ''

    async def execute(self, input_data: DockerManagerToolInput) -> DockerManagerToolOutput:
        """Execute tool."""
        return DockerManagerToolOutput(success=True, result='done')


class DockerManagerToolRegistry:
    """Tool registry."""

    def __init__(self):
        self._tools: dict[str, DockerManagerTool] = {}

    def register(self, tool: DockerManagerTool) -> None:
        """Register tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> DockerManagerTool | None:
        """Get tool."""
        return self._tools.get(name)

    def list_tools(self) -> list[DockerManagerTool]:
        """List tools."""
        return list(self._tools.values())

    async def execute(self, name: str, input_data: DockerManagerToolInput) -> DockerManagerToolOutput:
        """Execute tool."""
        tool = self._tools.get(name)
        if not tool:
            return DockerManagerToolOutput(success=False, error='Tool not found')
        return await tool.execute(input_data)
