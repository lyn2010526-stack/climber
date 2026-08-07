"""Tests for rate_limiting."""

import pytest

from app.modules.rate_limiting_module import (
    RateLimitingManager,
    RateLimitingType,
)


class TestRateLimitingManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = RateLimitingManager()
        await manager.initialize()
        item = await manager.create('test', RateLimitingType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = RateLimitingManager()
        item = await manager.create('test', RateLimitingType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = RateLimitingManager()
        item = await manager.create('test', RateLimitingType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = RateLimitingManager()
        await manager.create('a', RateLimitingType.TYPE_A)
        await manager.create('b', RateLimitingType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
