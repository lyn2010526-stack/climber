"""Tests for file_compressor tool."""

import pytest

from app.tools.file_compressor_tool import (
    FileCompressorTool,
    FileCompressorToolInput,
)


class TestFileCompressorTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = FileCompressorTool()
        inp = FileCompressorToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = FileCompressorTool()
        assert tool.name == 'file_compressor'
        assert tool.description
