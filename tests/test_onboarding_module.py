"""Tests for onboarding."""

import pytest

from app.modules.onboarding_module import (
    OnboardingManager,
    OnboardingType,
)


class TestOnboardingManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = OnboardingManager()
        await manager.initialize()
        item = await manager.create('test', OnboardingType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = OnboardingManager()
        item = await manager.create('test', OnboardingType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = OnboardingManager()
        item = await manager.create('test', OnboardingType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = OnboardingManager()
        await manager.create('a', OnboardingType.TYPE_A)
        await manager.create('b', OnboardingType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
