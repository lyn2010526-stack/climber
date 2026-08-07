"""Tests for in_app event."""


import pytest

from app.events.in_app_event import (
    InAppEvent,
    InAppEventBus,
)


class TestInAppEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = InAppEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = InAppEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = InAppEventBus()
        event = InAppEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = InAppEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
