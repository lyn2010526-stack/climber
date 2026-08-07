"""Tests for code_executor tool."""

import pytest

from app.tools.code_executor_tool import (
    CodeExecutorTool,
    CodeExecutorToolInput,
)


class TestCodeExecutorTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = CodeExecutorTool()
        inp = CodeExecutorToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = CodeExecutorTool()
        assert tool.name == 'code_executor'
        assert tool.description
