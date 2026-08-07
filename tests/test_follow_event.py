"""Tests for follow event."""


import pytest

from app.events.follow_event import (
    FollowEvent,
    FollowEventBus,
)


class TestFollowEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = FollowEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = FollowEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = FollowEventBus()
        event = FollowEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = FollowEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
