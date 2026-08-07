"""Tests for search."""

import pytest

from app.modules.search_module import (
    SearchManager,
    SearchType,
)


class TestSearchManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = SearchManager()
        await manager.initialize()
        item = await manager.create('test', SearchType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = SearchManager()
        item = await manager.create('test', SearchType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = SearchManager()
        item = await manager.create('test', SearchType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = SearchManager()
        await manager.create('a', SearchType.TYPE_A)
        await manager.create('b', SearchType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
