"""Tests for like event."""


import pytest

from app.events.like_event import (
    LikeEvent,
    LikeEventBus,
)


class TestLikeEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = LikeEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = LikeEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = LikeEventBus()
        event = LikeEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = LikeEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
