"""Tests for spreadsheet_reader tool."""

import pytest

from app.tools.spreadsheet_reader_tool import (
    SpreadsheetReaderTool,
    SpreadsheetReaderToolInput,
    SpreadsheetReaderToolRegistry,
)


class TestSpreadsheetReaderTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = SpreadsheetReaderTool()
        input_data = SpreadsheetReaderToolInput(query='test')
        result = await tool.execute(input_data)
        assert result.success

    def test_registry(self):
        registry = SpreadsheetReaderToolRegistry()
        tool = SpreadsheetReaderTool()
        registry.register(tool)
        assert registry.get(tool.name) is not None
