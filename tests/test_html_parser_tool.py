"""Tests for html_parser tool."""

import pytest

from app.tools.html_parser_tool import (
    HtmlParserTool,
    HtmlParserToolInput,
    HtmlParserToolRegistry,
)


class TestHtmlParserTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = HtmlParserTool()
        input_data = HtmlParserToolInput(query='test')
        result = await tool.execute(input_data)
        assert result.success

    def test_registry(self):
        registry = HtmlParserToolRegistry()
        tool = HtmlParserTool()
        registry.register(tool)
        assert registry.get(tool.name) is not None
