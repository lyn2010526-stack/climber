"""Tests for messaging event."""


import pytest

from app.events.messaging_event import (
    MessagingEvent,
    MessagingEventBus,
)


class TestMessagingEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = MessagingEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = MessagingEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = MessagingEventBus()
        event = MessagingEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = MessagingEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
