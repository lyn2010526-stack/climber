"""Tests for analytics."""

import pytest

from app.modules.analytics_module import (
    AnalyticsManager,
    AnalyticsType,
)


class TestAnalyticsManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = AnalyticsManager()
        await manager.initialize()
        item = await manager.create('test', AnalyticsType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = AnalyticsManager()
        item = await manager.create('test', AnalyticsType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = AnalyticsManager()
        item = await manager.create('test', AnalyticsType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = AnalyticsManager()
        await manager.create('a', AnalyticsType.TYPE_A)
        await manager.create('b', AnalyticsType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
