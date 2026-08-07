"""Tests for keyword_extractor tool."""

import pytest

from app.tools.keyword_extractor_tool import (
    KeywordExtractorTool,
    KeywordExtractorToolInput,
)


class TestKeywordExtractorTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = KeywordExtractorTool()
        inp = KeywordExtractorToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = KeywordExtractorTool()
        assert tool.name == 'keyword_extractor'
        assert tool.description
