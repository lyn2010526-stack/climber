"""Tests for feature_flags."""

import pytest

from app.modules.feature_flags_module import (
    FeatureFlagsManager,
    FeatureFlagsType,
)


class TestFeatureFlagsManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = FeatureFlagsManager()
        await manager.initialize()
        item = await manager.create('test', FeatureFlagsType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = FeatureFlagsManager()
        item = await manager.create('test', FeatureFlagsType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = FeatureFlagsManager()
        item = await manager.create('test', FeatureFlagsType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = FeatureFlagsManager()
        await manager.create('a', FeatureFlagsType.TYPE_A)
        await manager.create('b', FeatureFlagsType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
