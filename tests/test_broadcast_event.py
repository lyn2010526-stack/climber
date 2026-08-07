"""Tests for broadcast event."""


import pytest

from app.events.broadcast_event import (
    BroadcastEvent,
    BroadcastEventBus,
)


class TestBroadcastEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = BroadcastEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = BroadcastEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = BroadcastEventBus()
        event = BroadcastEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = BroadcastEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
