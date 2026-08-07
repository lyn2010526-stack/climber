"""Tests for audit event."""


import pytest

from app.events.audit_event import (
    AuditEvent,
    AuditEventBus,
)


class TestAuditEventBus:
    """Tests for event bus."""

    def test_subscribe(self):
        bus = AuditEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert sid is not None

    def test_unsubscribe(self):
        bus = AuditEventBus()
        sid = bus.subscribe(['created'], lambda e: None)
        assert bus.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_publish(self):
        bus = AuditEventBus()
        event = AuditEvent(event_type='created')
        await bus.publish(event)
        assert bus._event_queue.qsize() == 1

    def test_get_stats(self):
        bus = AuditEventBus()
        stats = bus.get_stats()
        assert 'processed' in stats
