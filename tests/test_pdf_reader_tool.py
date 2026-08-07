"""Tests for pdf_reader tool."""

import pytest

from app.tools.pdf_reader_tool import (
    PdfReaderTool,
    PdfReaderToolInput,
)


class TestPdfReaderTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = PdfReaderTool()
        inp = PdfReaderToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = PdfReaderTool()
        assert tool.name == 'pdf_reader'
        assert tool.description
