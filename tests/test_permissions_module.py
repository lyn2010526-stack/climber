"""Tests for permissions."""

import pytest

from app.modules.permissions_module import (
    PermissionsManager,
    PermissionsType,
)


class TestPermissionsManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = PermissionsManager()
        await manager.initialize()
        item = await manager.create('test', PermissionsType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = PermissionsManager()
        item = await manager.create('test', PermissionsType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = PermissionsManager()
        item = await manager.create('test', PermissionsType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = PermissionsManager()
        await manager.create('a', PermissionsType.TYPE_A)
        await manager.create('b', PermissionsType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
