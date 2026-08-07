"""Tests for diff_viewer tool."""

import pytest

from app.tools.diff_viewer_tool import (
    DiffViewerTool,
    DiffViewerToolInput,
    DiffViewerToolRegistry,
)


class TestDiffViewerTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = DiffViewerTool()
        input_data = DiffViewerToolInput(query='test')
        result = await tool.execute(input_data)
        assert result.success

    def test_registry(self):
        registry = DiffViewerToolRegistry()
        tool = DiffViewerTool()
        registry.register(tool)
        assert registry.get(tool.name) is not None
