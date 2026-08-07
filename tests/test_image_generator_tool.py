"""Tests for image_generator tool."""

import pytest

from app.tools.image_generator_tool import (
    ImageGeneratorTool,
    ImageGeneratorToolInput,
    ImageGeneratorToolRegistry,
)


class TestImageGeneratorTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = ImageGeneratorTool()
        input_data = ImageGeneratorToolInput(query='test')
        result = await tool.execute(input_data)
        assert result.success

    def test_registry(self):
        registry = ImageGeneratorToolRegistry()
        tool = ImageGeneratorTool()
        registry.register(tool)
        assert registry.get(tool.name) is not None
