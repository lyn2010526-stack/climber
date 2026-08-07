"""Tests for file_reader tool."""

import pytest

from app.tools.file_reader_tool import (
    FileReaderTool,
    FileReaderToolInput,
)


class TestFileReaderTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = FileReaderTool()
        inp = FileReaderToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = FileReaderTool()
        assert tool.name == 'file_reader'
        assert tool.description
