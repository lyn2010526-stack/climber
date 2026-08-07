"""Tests for web_search tool."""

import pytest

from app.tools.web_search_tool import (
    WebSearchTool,
    WebSearchToolInput,
)


class TestWebSearchTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = WebSearchTool()
        inp = WebSearchToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = WebSearchTool()
        assert tool.name == 'web_search'
        assert tool.description
