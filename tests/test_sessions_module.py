"""Tests for sessions."""

import pytest

from app.modules.sessions_module import (
    SessionsManager,
    SessionsType,
)


class TestSessionsManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = SessionsManager()
        await manager.initialize()
        item = await manager.create('test', SessionsType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = SessionsManager()
        item = await manager.create('test', SessionsType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = SessionsManager()
        item = await manager.create('test', SessionsType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = SessionsManager()
        await manager.create('a', SessionsType.TYPE_A)
        await manager.create('b', SessionsType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
