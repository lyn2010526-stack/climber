"""Tests for billing."""

import pytest

from app.modules.billing_module import (
    BillingManager,
    BillingType,
)


class TestBillingManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = BillingManager()
        await manager.initialize()
        item = await manager.create('test', BillingType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = BillingManager()
        item = await manager.create('test', BillingType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = BillingManager()
        item = await manager.create('test', BillingType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = BillingManager()
        await manager.create('a', BillingType.TYPE_A)
        await manager.create('b', BillingType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
