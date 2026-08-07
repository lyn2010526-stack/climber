"""Tests for data_analyzer tool."""

import pytest

from app.tools.data_analyzer_tool import (
    DataAnalyzerTool,
    DataAnalyzerToolInput,
    DataAnalyzerToolRegistry,
)


class TestDataAnalyzerTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = DataAnalyzerTool()
        input_data = DataAnalyzerToolInput(query='test')
        result = await tool.execute(input_data)
        assert result.success

    def test_registry(self):
        registry = DataAnalyzerToolRegistry()
        tool = DataAnalyzerTool()
        registry.register(tool)
        assert registry.get(tool.name) is not None
