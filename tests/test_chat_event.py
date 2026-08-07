"""Tests for chat event."""


import pytest

from app.events.chat_event import (
    ChatEvent,
    ChatEventBus,
)


class TestChatEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = ChatEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = ChatEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = ChatEventBus()
        event = ChatEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = ChatEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
