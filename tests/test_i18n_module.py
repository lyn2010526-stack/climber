"""Tests for i18n."""

import pytest

from app.modules.i18n_module import (
    I18nManager,
    I18nType,
)


class TestI18nManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = I18nManager()
        await manager.initialize()
        item = await manager.create('test', I18nType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = I18nManager()
        item = await manager.create('test', I18nType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = I18nManager()
        item = await manager.create('test', I18nType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = I18nManager()
        await manager.create('a', I18nType.TYPE_A)
        await manager.create('b', I18nType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
