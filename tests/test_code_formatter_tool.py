"""Tests for code_formatter tool."""

import pytest

from app.tools.code_formatter_tool import (
    CodeFormatterTool,
    CodeFormatterToolInput,
)


class TestCodeFormatterTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = CodeFormatterTool()
        inp = CodeFormatterToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = CodeFormatterTool()
        assert tool.name == 'code_formatter'
        assert tool.description
