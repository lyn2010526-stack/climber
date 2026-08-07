"""Tests for system event."""


import pytest

from app.events.system_event import (
    SystemEvent,
    SystemEventBus,
)


class TestSystemEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = SystemEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = SystemEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = SystemEventBus()
        event = SystemEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = SystemEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
