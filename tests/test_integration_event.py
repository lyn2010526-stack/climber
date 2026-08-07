"""Tests for integration event."""


import pytest

from app.events.integration_event import (
    IntegrationEvent,
    IntegrationEventBus,
)


class TestIntegrationEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = IntegrationEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = IntegrationEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = IntegrationEventBus()
        event = IntegrationEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = IntegrationEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
