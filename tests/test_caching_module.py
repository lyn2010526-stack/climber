"""Tests for caching."""

import pytest

from app.modules.caching_module import (
    CachingManager,
    CachingType,
)


class TestCachingManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = CachingManager()
        await manager.initialize()
        item = await manager.create('test', CachingType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = CachingManager()
        item = await manager.create('test', CachingType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = CachingManager()
        item = await manager.create('test', CachingType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = CachingManager()
        await manager.create('a', CachingType.TYPE_A)
        await manager.create('b', CachingType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
