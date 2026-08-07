"""Tests for user_action event."""


import pytest

from app.events.user_action_event import (
    UserActionEvent,
    UserActionEventBus,
)


class TestUserActionEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = UserActionEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = UserActionEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = UserActionEventBus()
        event = UserActionEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = UserActionEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
