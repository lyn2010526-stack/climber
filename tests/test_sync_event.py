"""Tests for sync event."""


import pytest

from app.events.sync_event import (
    SyncEvent,
    SyncEventBus,
)


class TestSyncEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = SyncEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = SyncEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = SyncEventBus()
        event = SyncEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = SyncEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
