"""Tests for the group collaboration WebSocket hub."""

from __future__ import annotations

import pytest

import app.core.group_ws_hub as hub_module
from app.core.group_ws_hub import SUPPORTED_EVENT_TYPES, GroupWebSocketHub


@pytest.fixture(autouse=True)
def _clean_connections():
    """Clear the module-level connection registry between tests."""
    hub_module._group_connections.clear()
    yield
    hub_module._group_connections.clear()


class FakeWS:
    """In-memory fake WebSocket that records sent messages."""

    def __init__(self):
        self.sent: list[dict] = []
        self.failed = False

    async def send_json(self, message: dict) -> None:
        if self.failed:
            raise RuntimeError("socket closed")
        self.sent.append(message)


@pytest.mark.asyncio
async def test_connect_and_broadcast_delivers_to_subscribers():
    hub = GroupWebSocketHub()
    ws1, ws2 = FakeWS(), FakeWS()
    await hub.connect("g1", ws1)
    await hub.connect("g1", ws2)

    await hub.broadcast("g1", {"type": "message", "data": {"ok": True}})

    assert len(ws1.sent) == 1
    assert len(ws2.sent) == 1
    assert ws1.sent[0]["type"] == "message"


@pytest.mark.asyncio
async def test_broadcast_does_not_leak_to_other_groups():
    hub = GroupWebSocketHub()
    ws1 = FakeWS()
    await hub.connect("g1", ws1)
    await hub.connect("g2", FakeWS())

    await hub.broadcast("g1", {"type": "message", "data": {}})

    assert len(ws1.sent) == 1


@pytest.mark.asyncio
async def test_broadcast_drops_dead_connections():
    hub = GroupWebSocketHub()
    dead, alive = FakeWS(), FakeWS()
    dead.failed = True
    await hub.connect("g1", dead)
    await hub.connect("g1", alive)

    await hub.broadcast("g1", {"type": "message", "data": {}})

    assert len(alive.sent) == 1
    assert len(hub_module._group_connections["g1"]) == 1


@pytest.mark.asyncio
async def test_disconnect_removes_connection():
    hub = GroupWebSocketHub()
    ws = FakeWS()
    await hub.connect("g1", ws)
    await hub.disconnect("g1", ws)

    assert "g1" not in hub_module._group_connections or len(hub_module._group_connections["g1"]) == 0


@pytest.mark.asyncio
async def test_unsupported_event_type_logs_but_still_broadcasts():
    hub = GroupWebSocketHub()
    ws = FakeWS()
    await hub.connect("g1", ws)

    await hub.broadcast("g1", {"type": "not_supported_at_all", "data": {}})

    assert len(ws.sent) == 1


@pytest.mark.asyncio
async def test_handle_message_unknown_type():
    hub = GroupWebSocketHub()
    result = await hub.handle_message("g1", {"type": "nope"})
    assert result == {"ok": False, "error": "unknown_type"}


@pytest.mark.asyncio
async def test_supported_event_types_are_complete():
    required = {
        "message",
        "task_update",
        "task_completed",
        "task_failed",
        "worker_tool_call",
        "human_review_needed",
        "human_review_approved",
        "error",
        "typing",
    }
    assert required.issubset(SUPPORTED_EVENT_TYPES)
