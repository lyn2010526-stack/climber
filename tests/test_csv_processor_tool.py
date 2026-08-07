"""Tests for csv_processor tool."""

import pytest

from app.tools.csv_processor_tool import (
    CsvProcessorTool,
    CsvProcessorToolInput,
    CsvProcessorToolRegistry,
)


class TestCsvProcessorTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = CsvProcessorTool()
        input_data = CsvProcessorToolInput(query='test')
        result = await tool.execute(input_data)
        assert result.success

    def test_registry(self):
        registry = CsvProcessorToolRegistry()
        tool = CsvProcessorTool()
        registry.register(tool)
        assert registry.get(tool.name) is not None
