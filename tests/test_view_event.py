"""Tests for view event."""


import pytest

from app.events.view_event import (
    ViewEvent,
    ViewEventBus,
)


class TestViewEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = ViewEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = ViewEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = ViewEventBus()
        event = ViewEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = ViewEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
