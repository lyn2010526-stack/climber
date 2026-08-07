"""Tests for chart_generator tool."""

import pytest

from app.tools.chart_generator_tool import (
    ChartGeneratorTool,
    ChartGeneratorToolInput,
    ChartGeneratorToolRegistry,
)


class TestChartGeneratorTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = ChartGeneratorTool()
        input_data = ChartGeneratorToolInput(query='test')
        result = await tool.execute(input_data)
        assert result.success

    def test_registry(self):
        registry = ChartGeneratorToolRegistry()
        tool = ChartGeneratorTool()
        registry.register(tool)
        assert registry.get(tool.name) is not None
