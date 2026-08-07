"""Tests for file_storage."""

import pytest

from app.modules.file_storage_module import (
    FileStorageManager,
    FileStorageType,
)


class TestFileStorageManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = FileStorageManager()
        await manager.initialize()
        item = await manager.create('test', FileStorageType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = FileStorageManager()
        item = await manager.create('test', FileStorageType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = FileStorageManager()
        item = await manager.create('test', FileStorageType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = FileStorageManager()
        await manager.create('a', FileStorageType.TYPE_A)
        await manager.create('b', FileStorageType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
