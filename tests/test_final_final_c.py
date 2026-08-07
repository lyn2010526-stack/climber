"""Tests for final_c."""

import pytest

from app.final.final_c_manager import (
    FinalCManager,
)


class TestFinalCManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = FinalCManager()
        item = await manager.create('test')
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = FinalCManager()
        item = await manager.create('test')
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = FinalCManager()
        item = await manager.create('test')
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = FinalCManager()
        await manager.create('a')
        await manager.create('b')
        items = await manager.list_items()
        assert len(items) == 2
