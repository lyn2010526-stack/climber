"""Tests for xml_parser tool."""

import pytest

from app.tools.xml_parser_tool import (
    XmlParserTool,
    XmlParserToolInput,
)


class TestXmlParserTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = XmlParserTool()
        inp = XmlParserToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = XmlParserTool()
        assert tool.name == 'xml_parser'
        assert tool.description
