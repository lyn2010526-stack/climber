"""Tests for subscriptions."""

import pytest

from app.modules.subscriptions_module import (
    SubscriptionsManager,
    SubscriptionsType,
)


class TestSubscriptionsManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = SubscriptionsManager()
        await manager.initialize()
        item = await manager.create('test', SubscriptionsType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = SubscriptionsManager()
        item = await manager.create('test', SubscriptionsType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = SubscriptionsManager()
        item = await manager.create('test', SubscriptionsType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = SubscriptionsManager()
        await manager.create('a', SubscriptionsType.TYPE_A)
        await manager.create('b', SubscriptionsType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
