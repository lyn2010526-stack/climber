"""Tests for ocr tool."""

import pytest

from app.tools.ocr_tool import (
    OcrTool,
    OcrToolInput,
)


class TestOcrTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = OcrTool()
        inp = OcrToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = OcrTool()
        assert tool.name == 'ocr'
        assert tool.description
