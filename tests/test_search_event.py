"""Tests for search event."""


import pytest

from app.events.search_event import (
    SearchEvent,
    SearchEventBus,
)


class TestSearchEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = SearchEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = SearchEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = SearchEventBus()
        event = SearchEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = SearchEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
