"""Tests for sso."""

import pytest

from app.modules.sso_module import (
    SsoManager,
    SsoType,
)


class TestSsoManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = SsoManager()
        await manager.initialize()
        item = await manager.create('test', SsoType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = SsoManager()
        item = await manager.create('test', SsoType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = SsoManager()
        item = await manager.create('test', SsoType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = SsoManager()
        await manager.create('a', SsoType.TYPE_A)
        await manager.create('b', SsoType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
