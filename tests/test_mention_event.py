"""Tests for mention event."""


import pytest

from app.events.mention_event import (
    MentionEvent,
    MentionEventBus,
)


class TestMentionEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = MentionEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = MentionEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = MentionEventBus()
        event = MentionEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = MentionEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
