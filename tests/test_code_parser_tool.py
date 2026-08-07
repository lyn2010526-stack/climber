"""Tests for code_parser tool."""

import pytest

from app.tools.code_parser_tool import (
    CodeParserTool,
    CodeParserToolInput,
    CodeParserToolRegistry,
)


class TestCodeParserTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = CodeParserTool()
        input_data = CodeParserToolInput(query='test')
        result = await tool.execute(input_data)
        assert result.success

    def test_registry(self):
        registry = CodeParserToolRegistry()
        tool = CodeParserTool()
        registry.register(tool)
        assert registry.get(tool.name) is not None
