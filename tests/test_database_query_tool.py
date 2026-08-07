"""Tests for database_query tool."""

import pytest

from app.tools.database_query_tool import (
    DatabaseQueryTool,
    DatabaseQueryToolInput,
)


class TestDatabaseQueryTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = DatabaseQueryTool()
        inp = DatabaseQueryToolInput(action='test')
        output = await tool.execute(inp)
        assert output.success is True
        assert output.result is not None

    def test_properties(self):
        tool = DatabaseQueryTool()
        assert tool.name == 'database_query'
        assert tool.description
