"""Tests for kubernetes_manager tool."""

import pytest

from app.tools.kubernetes_manager_tool import (
    KubernetesManagerTool,
    KubernetesManagerToolInput,
    KubernetesManagerToolRegistry,
)


class TestKubernetesManagerTool:
    """Tests for tool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = KubernetesManagerTool()
        input_data = KubernetesManagerToolInput(query='test')
        result = await tool.execute(input_data)
        assert result.success

    def test_registry(self):
        registry = KubernetesManagerToolRegistry()
        tool = KubernetesManagerTool()
        registry.register(tool)
        assert registry.get(tool.name) is not None
