"""Tests for summarizer tool."""

import pytest

from app.tools.summarizer_tool import (
    SummarizerTool,
    SummarizerToolInput,
)


class TestSummarizerTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = SummarizerTool()
        inp = SummarizerToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = SummarizerTool()
        assert tool.name == 'summarizer'
        assert tool.description
