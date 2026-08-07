"""Tests for scheduler tool."""

import pytest

from app.tools.scheduler_tool import (
    SchedulerTool,
    SchedulerToolInput,
    SchedulerToolRegistry,
)


class TestSchedulerTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = SchedulerTool()
        input_data = SchedulerToolInput(query='test')
        result = await tool.execute(input_data)
        assert result.success

    def test_registry(self):
        registry = SchedulerToolRegistry()
        tool = SchedulerTool()
        registry.register(tool)
        assert registry.get(tool.name) is not None
