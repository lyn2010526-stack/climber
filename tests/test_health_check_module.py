"""Tests for health_check."""

import pytest

from app.modules.health_check_module import (
    HealthCheckManager,
    HealthCheckType,
)


class TestHealthCheckManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = HealthCheckManager()
        await manager.initialize()
        item = await manager.create('test', HealthCheckType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = HealthCheckManager()
        item = await manager.create('test', HealthCheckType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = HealthCheckManager()
        item = await manager.create('test', HealthCheckType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = HealthCheckManager()
        await manager.create('a', HealthCheckType.TYPE_A)
        await manager.create('b', HealthCheckType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
