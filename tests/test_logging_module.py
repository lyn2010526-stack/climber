"""Tests for logging."""

import pytest

from app.modules.logging_module import (
    LoggingManager,
    LoggingType,
)


class TestLoggingManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = LoggingManager()
        await manager.initialize()
        item = await manager.create('test', LoggingType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = LoggingManager()
        item = await manager.create('test', LoggingType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = LoggingManager()
        item = await manager.create('test', LoggingType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = LoggingManager()
        await manager.create('a', LoggingType.TYPE_A)
        await manager.create('b', LoggingType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
