"""Tool: image_generator - Agent tool."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ImageGeneratorToolInput:
    """Tool input."""
    query: str = ''
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class ImageGeneratorToolOutput:
    """Tool output."""
    success: bool = False
    result: Any = None
    error: str | None = None


class ImageGeneratorTool:
    """Base tool."""

    name: str = 'image_generator'
    description: str = ''

    async def execute(self, input_data: ImageGeneratorToolInput) -> ImageGeneratorToolOutput:
        """Execute tool."""
        return ImageGeneratorToolOutput(success=True, result='done')


class ImageGeneratorToolRegistry:
    """Tool registry."""

    def __init__(self):
        self._tools: dict[str, ImageGeneratorTool] = {}

    def register(self, tool: ImageGeneratorTool) -> None:
        """Register tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> ImageGeneratorTool | None:
        """Get tool."""
        return self._tools.get(name)

    def list_tools(self) -> list[ImageGeneratorTool]:
        """List tools."""
        return list(self._tools.values())

    async def execute(self, name: str, input_data: ImageGeneratorToolInput) -> ImageGeneratorToolOutput:
        """Execute tool."""
        tool = self._tools.get(name)
        if not tool:
            return ImageGeneratorToolOutput(success=False, error='Tool not found')
        return await tool.execute(input_data)
