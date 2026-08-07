"""Tests for docker_manager tool."""

import pytest

from app.tools.docker_manager_tool import (
    DockerManagerTool,
    DockerManagerToolInput,
    DockerManagerToolRegistry,
)


class TestDockerManagerTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = DockerManagerTool()
        input_data = DockerManagerToolInput(query='test')
        result = await tool.execute(input_data)
        assert result.success

    def test_registry(self):
        registry = DockerManagerToolRegistry()
        tool = DockerManagerTool()
        registry.register(tool)
        assert registry.get(tool.name) is not None
