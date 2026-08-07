"""Tests for color_extractor tool."""

import pytest

from app.tools.color_extractor_tool import (
    ColorExtractorTool,
    ColorExtractorToolInput,
)


class TestColorExtractorTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = ColorExtractorTool()
        inp = ColorExtractorToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = ColorExtractorTool()
        assert tool.name == 'color_extractor'
        assert tool.description
