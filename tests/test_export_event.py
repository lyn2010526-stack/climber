"""Tests for export event."""


import pytest

from app.events.export_event import (
    ExportEvent,
    ExportEventBus,
)


class TestExportEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = ExportEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = ExportEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = ExportEventBus()
        event = ExportEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = ExportEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
