"""Tests for translator tool."""

import pytest

from app.tools.translator_tool import (
    TranslatorTool,
    TranslatorToolInput,
)


class TestTranslatorTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = TranslatorTool()
        inp = TranslatorToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = TranslatorTool()
        assert tool.name == 'translator'
        assert tool.description
