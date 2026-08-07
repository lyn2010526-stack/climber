"""Tests for payments."""

import pytest

from app.modules.payments_module import (
    PaymentsManager,
    PaymentsType,
)


class TestPaymentsManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = PaymentsManager()
        await manager.initialize()
        item = await manager.create('test', PaymentsType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = PaymentsManager()
        item = await manager.create('test', PaymentsType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = PaymentsManager()
        item = await manager.create('test', PaymentsType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = PaymentsManager()
        await manager.create('a', PaymentsType.TYPE_A)
        await manager.create('b', PaymentsType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
