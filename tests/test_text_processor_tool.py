"""Tests for text_processor tool."""

import pytest

from app.tools.text_processor_tool import (
    TextProcessorTool,
    TextProcessorToolInput,
)


class TestTextProcessorTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = TextProcessorTool()
        inp = TextProcessorToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = TextProcessorTool()
        assert tool.name == 'text_processor'
        assert tool.description
