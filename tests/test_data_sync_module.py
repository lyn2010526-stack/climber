"""Tests for data_sync."""

import pytest

from app.modules.data_sync_module import (
    DataSyncManager,
    DataSyncType,
)


class TestDataSyncManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = DataSyncManager()
        await manager.initialize()
        item = await manager.create('test', DataSyncType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = DataSyncManager()
        item = await manager.create('test', DataSyncType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = DataSyncManager()
        item = await manager.create('test', DataSyncType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = DataSyncManager()
        await manager.create('a', DataSyncType.TYPE_A)
        await manager.create('b', DataSyncType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
