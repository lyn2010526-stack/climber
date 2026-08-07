"""Tests for sentiment tool."""

import pytest

from app.tools.sentiment_tool import (
    SentimentTool,
    SentimentToolInput,
)


class TestSentimentTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = SentimentTool()
        inp = SentimentToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = SentimentTool()
        assert tool.name == 'sentiment'
        assert tool.description
