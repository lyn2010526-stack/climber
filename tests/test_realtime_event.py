"""Tests for realtime event."""


import pytest

from app.events.realtime_event import (
    RealtimeEvent,
    RealtimeEventBus,
)


class TestRealtimeEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = RealtimeEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = RealtimeEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = RealtimeEventBus()
        event = RealtimeEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = RealtimeEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
