"""Tests for image_processor tool."""

import pytest

from app.tools.image_processor_tool import (
    ImageProcessorTool,
    ImageProcessorToolInput,
)


class TestImageProcessorTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = ImageProcessorTool()
        inp = ImageProcessorToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = ImageProcessorTool()
        assert tool.name == 'image_processor'
        assert tool.description
