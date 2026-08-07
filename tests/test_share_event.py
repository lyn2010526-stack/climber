"""Tests for share event."""


import pytest

from app.events.share_event import (
    ShareEvent,
    ShareEventBus,
)


class TestShareEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = ShareEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = ShareEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = ShareEventBus()
        event = ShareEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = ShareEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
