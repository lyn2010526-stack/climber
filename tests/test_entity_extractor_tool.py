"""Tests for entity_extractor tool."""

import pytest

from app.tools.entity_extractor_tool import (
    EntityExtractorTool,
    EntityExtractorToolInput,
)


class TestEntityExtractorTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = EntityExtractorTool()
        inp = EntityExtractorToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = EntityExtractorTool()
        assert tool.name == 'entity_extractor'
        assert tool.description
