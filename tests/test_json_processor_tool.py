"""Tests for json_processor tool."""

import pytest

from app.tools.json_processor_tool import (
    JsonProcessorTool,
    JsonProcessorToolInput,
    JsonProcessorToolRegistry,
)


class TestJsonProcessorTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = JsonProcessorTool()
        input_data = JsonProcessorToolInput(query='test')
        result = await tool.execute(input_data)
        assert result.success

    def test_registry(self):
        registry = JsonProcessorToolRegistry()
        tool = JsonProcessorTool()
        registry.register(tool)
        assert registry.get(tool.name) is not None
