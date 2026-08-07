"""Tests for webhook event."""


import pytest

from app.events.webhook_event import (
    WebhookEvent,
    WebhookEventBus,
)


class TestWebhookEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = WebhookEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = WebhookEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = WebhookEventBus()
        event = WebhookEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = WebhookEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
