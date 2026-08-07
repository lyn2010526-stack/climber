"""Tests for xml_processor tool."""

import pytest

from app.tools.xml_processor_tool import (
    XmlProcessorTool,
    XmlProcessorToolInput,
    XmlProcessorToolRegistry,
)


class TestXmlProcessorTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = XmlProcessorTool()
        input_data = XmlProcessorToolInput(query='test')
        result = await tool.execute(input_data)
        assert result.success

    def test_registry(self):
        registry = XmlProcessorToolRegistry()
        tool = XmlProcessorTool()
        registry.register(tool)
        assert registry.get(tool.name) is not None
