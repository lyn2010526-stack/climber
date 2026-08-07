"""Tests for language_detector tool."""

import pytest

from app.tools.language_detector_tool import (
    LanguageDetectorTool,
    LanguageDetectorToolInput,
)


class TestLanguageDetectorTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = LanguageDetectorTool()
        inp = LanguageDetectorToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = LanguageDetectorTool()
        assert tool.name == 'language_detector'
        assert tool.description
