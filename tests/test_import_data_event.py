"""Tests for import_data event."""


import pytest

from app.events.import_data_event import (
    ImportDataEvent,
    ImportDataEventBus,
)


class TestImportDataEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = ImportDataEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = ImportDataEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = ImportDataEventBus()
        event = ImportDataEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = ImportDataEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
