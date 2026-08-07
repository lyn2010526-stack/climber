"""Tests for webhooks."""

import pytest

from app.modules.webhooks_module import (
    WebhooksManager,
    WebhooksType,
)


class TestWebhooksManager:
    """Tests for manager."""

    @pytest.mark.asyncio
    async def test_create_and_get(self):
        manager = WebhooksManager()
        await manager.initialize()
        item = await manager.create('test', WebhooksType.TYPE_A)
        assert item.name == 'test'
        found = await manager.get(item.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_update(self):
        manager = WebhooksManager()
        item = await manager.create('test', WebhooksType.TYPE_A)
        updated = await manager.update(item.id, name='updated')
        assert updated is not None
        assert updated.name == 'updated'

    @pytest.mark.asyncio
    async def test_delete(self):
        manager = WebhooksManager()
        item = await manager.create('test', WebhooksType.TYPE_A)
        result = await manager.delete(item.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_items(self):
        manager = WebhooksManager()
        await manager.create('a', WebhooksType.TYPE_A)
        await manager.create('b', WebhooksType.TYPE_B)
        result = await manager.list_items()
        assert result.total == 2
