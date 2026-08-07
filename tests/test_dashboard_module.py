"""Tests for dashboard."""

import pytest

from app.modules.dashboard_module import (
    DashboardManager,
    DashboardType,
)


class TestDashboardManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = DashboardManager()
        await manager.initialize()
        item = await manager.create('test', DashboardType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = DashboardManager()
        item = await manager.create('test', DashboardType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = DashboardManager()
        item = await manager.create('test', DashboardType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = DashboardManager()
        await manager.create('a', DashboardType.TYPE_A)
        await manager.create('b', DashboardType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
