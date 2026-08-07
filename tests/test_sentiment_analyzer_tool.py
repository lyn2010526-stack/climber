"""Tests for sentiment_analyzer tool."""

import pytest

from app.tools.sentiment_analyzer_tool import (
    SentimentAnalyzerTool,
    SentimentAnalyzerToolInput,
    SentimentAnalyzerToolRegistry,
)


class TestSentimentAnalyzerTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = SentimentAnalyzerTool()
        input_data = SentimentAnalyzerToolInput(query='test')
        result = await tool.execute(input_data)
        assert result.success

    def test_registry(self):
        registry = SentimentAnalyzerToolRegistry()
        tool = SentimentAnalyzerTool()
        registry.register(tool)
        assert registry.get(tool.name) is not None
