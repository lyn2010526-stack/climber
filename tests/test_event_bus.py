"""Tests for the event bus system."""

import pytest

from app.core.event_bus import EventBus


@pytest.fixture
def bus():
    return EventBus(history_size=100)


class TestEventBus:
    @pytest.mark.asyncio
    async def test_publish_subscribe(self, bus):
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe("test_event", handler)
        await bus.publish("test_event", {"key": "value"})

        assert len(received) == 1
        assert received[0]["type"] == "test_event"
        assert received[0]["key"] == "value"

    @pytest.mark.asyncio
    async def test_global_subscriber(self, bus):
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe(None, handler)
        await bus.publish("event_a", {"a": 1})
        await bus.publish("event_b", {"b": 2})

        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_filter_function(self, bus):
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe("test_event", handler, filter_fn=lambda e: e.get("priority") == "high")
        await bus.publish("test_event", {"priority": "low"})
        await bus.publish("test_event", {"priority": "high"})

        assert len(received) == 1
        assert received[0]["priority"] == "high"

    @pytest.mark.asyncio
    async def test_unsubscribe(self, bus):
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe("test_event", handler)
        await bus.publish("test_event", {"key": "value"})
        assert len(received) == 1

        bus.unsubscribe("test_event", handler)
        await bus.publish("test_event", {"key": "value2"})
        assert len(received) == 1  # no new event

    @pytest.mark.asyncio
    async def test_history(self, bus):
        await bus.publish("event_a", {"a": 1})
        await bus.publish("event_b", {"b": 2})
        await bus.publish("event_a", {"a": 3})

        history = bus.get_history()
        assert len(history) == 3

        history_a = bus.get_history(event_type="event_a")
        assert len(history_a) == 2

    @pytest.mark.asyncio
    async def test_clear_history(self, bus):
        await bus.publish("event", {"data": 1})
        bus.clear_history()
        assert len(bus.get_history()) == 0

    @pytest.mark.asyncio
    async def test_subscriber_error_does_not_break_publish(self, bus):
        async def bad_handler(event):
            raise ValueError("handler error")

        received = []
        async def good_handler(event):
            received.append(event)

        bus.subscribe("test", bad_handler)
        bus.subscribe("test", good_handler)

        await bus.publish("test", {"key": "value"})
        assert len(received) == 1
