"""Tests for event_bus."""

import pytest

from app.modules.event_bus_module import (
    EventBusManager,
    EventBusType,
)


class TestEventBusManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = EventBusManager()
        await manager.initialize()
        item = await manager.create('test', EventBusType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = EventBusManager()
        item = await manager.create('test', EventBusType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = EventBusManager()
        item = await manager.create('test', EventBusType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = EventBusManager()
        await manager.create('a', EventBusType.TYPE_A)
        await manager.create('b', EventBusType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
