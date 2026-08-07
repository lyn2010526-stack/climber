"""Tests for web_scraper tool."""

import pytest

from app.tools.web_scraper_tool import (
    WebScraperTool,
    WebScraperToolInput,
)


class TestWebScraperTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = WebScraperTool()
        inp = WebScraperToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = WebScraperTool()
        assert tool.name == 'web_scraper'
        assert tool.description
