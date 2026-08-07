"""Tests for reaction event."""


import pytest

from app.events.reaction_event import (
    ReactionEvent,
    ReactionEventBus,
)


class TestReactionEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = ReactionEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = ReactionEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = ReactionEventBus()
        event = ReactionEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = ReactionEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
