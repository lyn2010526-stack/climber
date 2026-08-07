"""Tests for csv_parser tool."""

import pytest

from app.tools.csv_parser_tool import (
    CsvParserTool,
    CsvParserToolInput,
)


class TestCsvParserTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = CsvParserTool()
        inp = CsvParserToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = CsvParserTool()
        assert tool.name == 'csv_parser'
        assert tool.description
