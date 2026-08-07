"""Tests for text_classifier tool."""

import pytest

from app.tools.text_classifier_tool import (
    TextClassifierTool,
    TextClassifierToolInput,
)


class TestTextClassifierTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = TextClassifierTool()
        inp = TextClassifierToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = TextClassifierTool()
        assert tool.name == 'text_classifier'
        assert tool.description
