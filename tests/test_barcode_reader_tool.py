"""Tests for barcode_reader tool."""

import pytest

from app.tools.barcode_reader_tool import (
    BarcodeReaderTool,
    BarcodeReaderToolInput,
)


class TestBarcodeReaderTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = BarcodeReaderTool()
        inp = BarcodeReaderToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = BarcodeReaderTool()
        assert tool.name == 'barcode_reader'
        assert tool.description
