"""Tests for roles."""

import pytest

from app.modules.roles_module import (
    RolesManager,
    RolesType,
)


class TestRolesManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = RolesManager()
        await manager.initialize()
        item = await manager.create('test', RolesType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = RolesManager()
        item = await manager.create('test', RolesType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = RolesManager()
        item = await manager.create('test', RolesType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = RolesManager()
        await manager.create('a', RolesType.TYPE_A)
        await manager.create('b', RolesType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
