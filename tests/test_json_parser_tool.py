"""Tests for json_parser tool."""

import pytest

from app.tools.json_parser_tool import (
    JsonParserTool,
    JsonParserToolInput,
)


class TestJsonParserTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = JsonParserTool()
        inp = JsonParserToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = JsonParserTool()
        assert tool.name == 'json_parser'
        assert tool.description
