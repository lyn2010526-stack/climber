"""Tests for metrics."""

import pytest

from app.modules.metrics_module import (
    MetricsManager,
    MetricsType,
)


class TestMetricsManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = MetricsManager()
        await manager.initialize()
        item = await manager.create('test', MetricsType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = MetricsManager()
        item = await manager.create('test', MetricsType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = MetricsManager()
        item = await manager.create('test', MetricsType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = MetricsManager()
        await manager.create('a', MetricsType.TYPE_A)
        await manager.create('b', MetricsType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
