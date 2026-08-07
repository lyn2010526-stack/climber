"""Tests for push event."""


import pytest

from app.events.push_event import (
    PushEvent,
    PushEventBus,
)


class TestPushEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = PushEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = PushEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = PushEventBus()
        event = PushEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = PushEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
