"""Tests for video_analyzer tool."""

import pytest

from app.tools.video_analyzer_tool import (
    VideoAnalyzerTool,
    VideoAnalyzerToolInput,
    VideoAnalyzerToolRegistry,
)


class TestVideoAnalyzerTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = VideoAnalyzerTool()
        input_data = VideoAnalyzerToolInput(query='test')
        result = await tool.execute(input_data)
        assert result.success

    def test_registry(self):
        registry = VideoAnalyzerToolRegistry()
        tool = VideoAnalyzerTool()
        registry.register(tool)
        assert registry.get(tool.name) is not None
