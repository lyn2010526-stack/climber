"""Tests for code_linter tool."""

import pytest

from app.tools.code_linter_tool import (
    CodeLinterTool,
    CodeLinterToolInput,
)


class TestCodeLinterTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = CodeLinterTool()
        inp = CodeLinterToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = CodeLinterTool()
        assert tool.name == 'code_linter'
        assert tool.description
