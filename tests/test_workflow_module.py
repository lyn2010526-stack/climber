"""Tests for workflow."""

import pytest

from app.modules.workflow_module import (
    WorkflowManager,
    WorkflowType,
)


class TestWorkflowManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = WorkflowManager()
        await manager.initialize()
        item = await manager.create('test', WorkflowType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = WorkflowManager()
        item = await manager.create('test', WorkflowType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = WorkflowManager()
        item = await manager.create('test', WorkflowType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = WorkflowManager()
        await manager.create('a', WorkflowType.TYPE_A)
        await manager.create('b', WorkflowType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
