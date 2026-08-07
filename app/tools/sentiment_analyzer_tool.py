"""Tool: sentiment_analyzer - Agent tool."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SentimentAnalyzerToolInput:
    """Tool input."""
    query: str = ''
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class SentimentAnalyzerToolOutput:
    """Tool output."""
    success: bool = False
    result: Any = None
    error: str | None = None


class SentimentAnalyzerTool:
    """Base tool."""

    name: str = 'sentiment_analyzer'
    description: str = ''

    async def execute(self, input_data: SentimentAnalyzerToolInput) -> SentimentAnalyzerToolOutput:
        """Execute tool."""
        return SentimentAnalyzerToolOutput(success=True, result='done')


class SentimentAnalyzerToolRegistry:
    """Tool registry."""

    def __init__(self):
        self._tools: dict[str, SentimentAnalyzerTool] = {}

    def register(self, tool: SentimentAnalyzerTool) -> None:
        """Register tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> SentimentAnalyzerTool | None:
        """Get tool."""
        return self._tools.get(name)

    def list_tools(self) -> list[SentimentAnalyzerTool]:
        """List tools."""
        return list(self._tools.values())

    async def execute(self, name: str, input_data: SentimentAnalyzerToolInput) -> SentimentAnalyzerToolOutput:
        """Execute tool."""
        tool = self._tools.get(name)
        if not tool:
            return SentimentAnalyzerToolOutput(success=False, error='Tool not found')
        return await tool.execute(input_data)
