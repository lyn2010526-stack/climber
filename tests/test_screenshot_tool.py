"""Tests for screenshot tool."""

import pytest

from app.tools.screenshot_tool import (
    ScreenshotTool,
    ScreenshotToolInput,
)


class TestScreenshotTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = ScreenshotTool()
        inp = ScreenshotToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = ScreenshotTool()
        assert tool.name == 'screenshot'
        assert tool.description
