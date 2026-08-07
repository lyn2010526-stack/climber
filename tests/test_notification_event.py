"""Tests for notification event."""


import pytest

from app.events.notification_event import (
    NotificationEvent,
    NotificationEventBus,
)


class TestNotificationEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = NotificationEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = NotificationEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = NotificationEventBus()
        event = NotificationEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = NotificationEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
