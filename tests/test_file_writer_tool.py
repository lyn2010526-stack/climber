"""Tests for file_writer tool."""

import pytest

from app.tools.file_writer_tool import (
    FileWriterTool,
    FileWriterToolInput,
)


class TestFileWriterTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = FileWriterTool()
        inp = FileWriterToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = FileWriterTool()
        assert tool.name == 'file_writer'
        assert tool.description
