"""Tests for comment event."""


import pytest

from app.events.comment_event import (
    CommentEvent,
    CommentEventBus,
)


class TestCommentEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = CommentEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = CommentEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = CommentEventBus()
        event = CommentEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = CommentEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
