"""Tests for cache_invalidation event."""


import pytest

from app.events.cache_invalidation_event import (
    CacheInvalidationEvent,
    CacheInvalidationEventBus,
)


class TestCacheInvalidationEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = CacheInvalidationEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = CacheInvalidationEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = CacheInvalidationEventBus()
        event = CacheInvalidationEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = CacheInvalidationEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
