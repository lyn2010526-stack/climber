"""Tests for scheduler event."""


import pytest

from app.events.scheduler_event import (
    SchedulerEvent,
    SchedulerEventBus,
)


class TestSchedulerEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = SchedulerEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = SchedulerEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = SchedulerEventBus()
        event = SchedulerEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = SchedulerEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
