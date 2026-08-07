"""Tests for git_operator tool."""

import pytest

from app.tools.git_operator_tool import (
    GitOperatorTool,
    GitOperatorToolInput,
    GitOperatorToolRegistry,
)


class TestGitOperatorTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = GitOperatorTool()
        input_data = GitOperatorToolInput(query='test')
        result = await tool.execute(input_data)
        assert result.success

    def test_registry(self):
        registry = GitOperatorToolRegistry()
        tool = GitOperatorTool()
        registry.register(tool)
        assert registry.get(tool.name) is not None
