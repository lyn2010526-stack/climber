"""Tests for qr_generator tool."""

import pytest

from app.tools.qr_generator_tool import (
    QrGeneratorTool,
    QrGeneratorToolInput,
)


class TestQrGeneratorTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = QrGeneratorTool()
        inp = QrGeneratorToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = QrGeneratorTool()
        assert tool.name == 'qr_generator'
        assert tool.description
