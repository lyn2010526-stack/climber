"""Tests for email."""

import pytest

from app.modules.email_module import (
    EmailManager,
    EmailType,
)


class TestEmailManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = EmailManager()
        await manager.initialize()
        item = await manager.create('test', EmailType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = EmailManager()
        item = await manager.create('test', EmailType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = EmailManager()
        item = await manager.create('test', EmailType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = EmailManager()
        await manager.create('a', EmailType.TYPE_A)
        await manager.create('b', EmailType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
