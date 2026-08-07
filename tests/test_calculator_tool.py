"""Tests for calculator tool."""

import pytest

from app.tools.calculator_tool import (
    CalculatorTool,
    CalculatorToolInput,
)


class TestCalculatorTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = CalculatorTool()
        inp = CalculatorToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = CalculatorTool()
        assert tool.name == 'calculator'
        assert tool.description
