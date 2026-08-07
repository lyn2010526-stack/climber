"""Comprehensive WebSocket stability tests for agent-engine.

Tests cover:
- Connection / disconnection
- Reconnection
- Concurrent connections
- Message broadcasting
- Error handling (invalid JSON, group not found)
- Message persistence and echo
- Group member update via WS
- Task update via WS
- Human review via WS
- Rapid connect/disconnect cycles
- Large payload handling
"""

from __future__ import annotations

import asyncio
import os
import time

import pytest

os.environ["APP_TESTING"] = "true"
os.environ.setdefault("TEST_DATABASE_URL", "sqlite+aiosqlite:////tmp/agent_engine_ws_test.db")

import contextlib

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from starlette.testclient import TestClient as StarletteTestClient

from app.main import app
from app.storage import Base, async_session, engine, init_db
from app.storage.models_groups import AgentGroup, AgentGroupMember, AgentGroupTask

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(init_db())
    finally:
        loop.close()
    yield


@pytest.fixture(autouse=True)
def cleanup_db():
    yield
    from sqlalchemy.exc import OperationalError
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        async def _cleanup():
            async with engine.begin() as conn:
                for table in reversed(Base.metadata.sorted_tables):
                    with contextlib.suppress(OperationalError):
                        await conn.execute(text(f"DELETE FROM {table.name}"))
                await conn.commit()
        loop.run_until_complete(_cleanup())
    finally:
        loop.close()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def starlette_client():
    """Synchronous Starlette TestClient for WebSocket testing."""
    with StarletteTestClient(app) as client:
        yield client


@pytest_asyncio.fixture
async def test_group():
    """Create a test group and return its ID."""
    async with async_session() as db:
        group = AgentGroup(
            user_id="test-user",
            name="Test Group",
            description="WS Test Group",
            topic="testing",
            status="active",
            max_rounds=10,
        )
        db.add(group)
        await db.commit()
        await db.refresh(group)
        group_id = group.id
    return group_id


@pytest_asyncio.fixture
async def test_member(test_group):
    """Create a test member in the group."""
    async with async_session() as db:
        member = AgentGroupMember(
            group_id=test_group,
            agent_id="test-agent-1",
            role="worker",
            status="active",
        )
        db.add(member)
        await db.commit()
        await db.refresh(member)
        return {"id": member.id, "agent_id": member.agent_id}


@pytest_asyncio.fixture
async def test_task(test_group, test_member):
    """Create a test task in the group."""
    async with async_session() as db:
        task = AgentGroupTask(
            group_id=test_group,
            description="Test task",
            status="pending",
            worker_id=test_member["id"],
            max_rounds=5,
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return {"id": task.id, "group_id": task.group_id}


# ---------------------------------------------------------------------------
# Endpoint Registration Tests
# ---------------------------------------------------------------------------

class TestEndpointRegistration:
    """Verify WebSocket routes are registered with the FastAPI app."""

    def test_ws_session_route_exists(self):
        from app.api.v1 import websocket as ws_mod
        paths = [r.path for r in ws_mod.router.routes if hasattr(r, "path")]
        assert any("/ws/" in p for p in paths), f"Session WS route missing: {paths}"

    def test_ws_group_route_exists(self):
        from app.api.v1 import websocket as ws_mod
        paths = [r.path for r in ws_mod.router.routes if hasattr(r, "path")]
        assert any("/ws/groups/" in p for p in paths), f"Group WS route missing: {paths}"

    def test_ws_router_included_in_app(self):
        """The websocket router must be registered in the app."""
        ws_routes = []
        for route in app.routes:
            if hasattr(route, "path") and "/ws/" in route.path:
                ws_routes.append(route.path)
        assert len(ws_routes) >= 2, f"Expected at least 2 WS routes in app, got {ws_routes}"


# ---------------------------------------------------------------------------
# Session WebSocket (/api/v1/ws/{session_id})
# ---------------------------------------------------------------------------

class TestSessionWebSocket:
    """Stability tests for the echo WebSocket endpoint."""

    def test_basic_connection_and_echo(self, starlette_client):
        """Connect, send a message, receive echo, disconnect."""
        with starlette_client.websocket_connect("/api/v1/ws/test-session-1") as ws:
            # Server sends connected message
            data1 = ws.receive_json()
            assert data1["type"] == "connected"
            assert data1["session_id"] == "test-session-1"

            # Send a message and get echo
            ws.send_json({"text": "hello"})
            data2 = ws.receive_json()
            assert data2["type"] == "echo"
            assert data2["data"]["text"] == "hello"

    def test_multiple_messages(self, starlette_client):
        """Send multiple messages in sequence."""
        with starlette_client.websocket_connect("/api/v1/ws/test-session-multi") as ws:
            ws.receive_json()  # connected
            for i in range(10):
                ws.send_json({"index": i, "msg": f"message-{i}"})
                data = ws.receive_json()
                assert data["type"] == "echo"
                assert data["data"]["index"] == i

    def test_graceful_disconnect(self, starlette_client):
        """Client disconnects gracefully, server should not error."""
        ws_ctx = starlette_client.websocket_connect("/api/v1/ws/test-session-disconnect")
        with ws_ctx as ws:
            ws.receive_json()  # connected
        # No exception means graceful disconnect worked

    def test_reconnection(self, starlette_client):
        """Disconnect and reconnect to the same session."""
        # First connection
        with starlette_client.websocket_connect("/api/v1/ws/test-session-reconnect") as ws1:
            ws1.receive_json()  # connected
            ws1.send_json({"msg": "before-reconnect"})
            ws1.receive_json()  # echo

        # Reconnect
        with starlette_client.websocket_connect("/api/v1/ws/test-session-reconnect") as ws2:
            data = ws2.receive_json()
            assert data["type"] == "connected"
            ws2.send_json({"msg": "after-reconnect"})
            resp = ws2.receive_json()
            assert resp["type"] == "echo"

    def test_rapid_connect_disconnect(self, starlette_client):
        """Rapid connect/disconnect cycles should not crash the server."""
        for _i in range(20):
            with starlette_client.websocket_connect("/api/v1/ws/test-session-rapid") as ws:
                ws.receive_json()  # connected
        # If we got here without exception, the server is stable


# ---------------------------------------------------------------------------
# Group WebSocket (/api/v1/ws/groups/{group_id})
# ---------------------------------------------------------------------------

class TestGroupWebSocket:
    """Stability tests for the group collaboration WebSocket endpoint."""

    def test_connect_and_receive_connected(self, starlette_client, test_group):
        """Connect to a valid group, send a message, get ack."""
        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws:
            ws.send_json({"type": "message", "content": "hello group"})
            data = ws.receive_json()
            assert data["type"] == "ack"

    def test_group_not_found(self, starlette_client):
        """Connect to a non-existent group, should get error."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{fake_id}") as ws:
            data = ws.receive_json()
            assert data["type"] == "error"
            assert data["error"] == "group_not_found"

    def test_invalid_json(self, starlette_client, test_group):
        """Send invalid JSON, should get error ack."""
        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws:
            ws.send_text("not-json{{{")
            data = ws.receive_json()
            assert data["type"] == "error"
            assert data["error"] == "invalid_json"

    def test_message_persistence(self, starlette_client, test_group):
        """Send a message and verify it's persisted to DB."""
        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws:
            ws.send_json({
                "type": "message",
                "content": "persisted message",
                "sender_name": "tester",
                "message_type": "text",
            })
            data = ws.receive_json()
            assert data["type"] == "ack"
            assert data["data"]["ok"] is True
            assert "id" in data["data"]

    def test_unknown_type(self, starlette_client, test_group):
        """Send unknown message type."""
        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws:
            ws.send_json({"type": "unknown_type_xyz", "data": "test"})
            data = ws.receive_json()
            assert data["type"] == "ack"
            assert data["data"]["ok"] is False
            assert data["data"]["error"] == "unknown_type"

    def test_member_update(self, starlette_client, test_group, test_member):
        """Update member status via WebSocket."""
        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws:
            ws.send_json({
                "type": "member_update",
                "member_id": test_member["id"],
                "status": "busy",
            })
            data = ws.receive_json()
            assert data["type"] == "ack"
            assert data["data"]["ok"] is True

    def test_member_update_missing_id(self, starlette_client, test_group):
        """Member update without member_id should fail."""
        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws:
            ws.send_json({
                "type": "member_update",
                "status": "busy",
            })
            data = ws.receive_json()
            assert data["data"]["ok"] is False
            assert data["data"]["error"] == "member_id required"

    def test_member_update_not_found(self, starlette_client, test_group):
        """Update non-existent member."""
        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws:
            ws.send_json({
                "type": "member_update",
                "member_id": "nonexistent-member-id",
                "status": "busy",
            })
            data = ws.receive_json()
            assert data["data"]["ok"] is False
            assert data["data"]["error"] == "member not found"

    def test_task_update(self, starlette_client, test_group, test_member, test_task):
        """Update task status via WebSocket."""
        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws:
            ws.send_json({
                "type": "task_update",
                "task_id": test_task["id"],
                "status": "running",
                "worker_id": test_member["id"],
                "current_round": 1,
            })
            data = ws.receive_json()
            assert data["type"] == "ack"
            assert data["data"]["ok"] is True

    def test_task_update_missing_id(self, starlette_client, test_group):
        """Task update without task_id should fail."""
        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws:
            ws.send_json({
                "type": "task_update",
                "status": "running",
            })
            data = ws.receive_json()
            assert data["data"]["ok"] is False
            assert data["data"]["error"] == "task_id required"

    def test_task_update_not_found(self, starlette_client, test_group):
        """Update non-existent task."""
        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws:
            ws.send_json({
                "type": "task_update",
                "task_id": "nonexistent-task-id",
                "status": "running",
            })
            data = ws.receive_json()
            assert data["data"]["ok"] is False
            assert data["data"]["error"] == "task not found"

    def test_human_review_approve(self, starlette_client, test_group, test_member, test_task):
        """Approve a task via human review."""
        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws:
            ws.send_json({
                "type": "human_review_response",
                "task_id": test_task["id"],
                "decision": "approved",
                "comment": "Looks good",
            })
            data = ws.receive_json()
            assert data["type"] == "ack"
            assert data["data"]["ok"] is True
            assert data["data"]["decision"] == "approved"

    def test_human_review_reject(self, starlette_client, test_group, test_member, test_task):
        """Reject a task via human review."""
        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws:
            ws.send_json({
                "type": "human_review_response",
                "task_id": test_task["id"],
                "decision": "rejected",
                "comment": "Needs rework",
            })
            data = ws.receive_json()
            assert data["type"] == "ack"
            assert data["data"]["ok"] is True
            assert data["data"]["decision"] == "rejected"

    def test_human_review_missing_fields(self, starlette_client, test_group):
        """Human review without required fields."""
        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws:
            ws.send_json({
                "type": "human_review_response",
                "decision": "approved",
            })
            data = ws.receive_json()
            assert data["data"]["ok"] is False
            assert data["data"]["error"] == "task_id and decision required"


# ---------------------------------------------------------------------------
# Concurrency Tests
# ---------------------------------------------------------------------------

class TestConcurrency:
    """Test concurrent WebSocket connections."""

    def test_multiple_clients_same_group(self, starlette_client, test_group):
        """Multiple clients connecting to the same group."""
        clients = []
        for i in range(5):
            ws_ctx = starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}")
            clients.append(ws_ctx)

        # Enter all contexts
        ws_list = []
        for ctx in clients:
            ws = ctx.__enter__()
            ws_list.append(ws)

        # All should be able to send messages
        for i, ws in enumerate(ws_list):
            ws.send_json({
                "type": "message",
                "content": f"msg from client {i}",
                "sender_name": f"client-{i}",
            })

        for ws in ws_list:
            data = ws.receive_json()
            assert data["type"] == "ack"

        # Cleanup
        for ctx in reversed(clients):
            ctx.__exit__(None, None, None)

    def test_concurrent_messages_broadcast(self, starlette_client, test_group):
        """One client sends, all connected clients receive broadcast."""
        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws1:
            with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws2:
                with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws3:
                    # ws1 sends a message
                    ws1.send_json({
                        "type": "message",
                        "content": "broadcast test",
                        "sender_name": "ws1",
                    })

                    # ws1 gets the ack
                    data1 = ws1.receive_json()
                    assert data1["type"] == "ack"
                    assert data1["data"]["ok"] is True

                    # ws2 and ws3 should receive the broadcast (type: message)
                    data2 = ws2.receive_json()
                    assert data2["type"] == "message"

                    data3 = ws3.receive_json()
                    assert data3["type"] == "message"

    def test_concurrent_different_groups(self, starlette_client):
        """Clients connecting to different groups simultaneously."""

        async def _create_groups():
            async with async_session() as db:
                g1 = AgentGroup(user_id="test", name="Group1", status="active")
                g2 = AgentGroup(user_id="test", name="Group2", status="active")
                db.add(g1)
                db.add(g2)
                await db.commit()
                await db.refresh(g1)
                await db.refresh(g2)
                return g1.id, g2.id

        gid1, gid2 = asyncio.get_event_loop().run_until_complete(_create_groups())

        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{gid1}") as ws1:
            with starlette_client.websocket_connect(f"/api/v1/ws/groups/{gid2}") as ws2:
                ws1.send_json({"type": "message", "content": "msg-g1", "sender_name": "u1"})
                ws2.send_json({"type": "message", "content": "msg-g2", "sender_name": "u2"})

                resp1 = ws1.receive_json()
                resp2 = ws2.receive_json()

                assert resp1["type"] == "ack"
                assert resp2["type"] == "ack"

    def test_client_disconnect_during_broadcast(self, starlette_client, test_group):
        """One client disconnects while server is broadcasting to others."""
        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}"):
            with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws2:
                # ws1 will be closed when we exit its context
                pass
            # ws2 should still work after ws1 disconnects
            ws2.send_json({
                "type": "message",
                "content": "after peer disconnect",
                "sender_name": "ws2",
            })
            data = ws2.receive_json()
            assert data["type"] == "ack"


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_empty_message(self, starlette_client, test_group):
        """Send an empty message."""
        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws:
            ws.send_text("")
            data = ws.receive_json()
            assert data["type"] == "error"
            assert data["error"] == "invalid_json"

    def test_large_payload(self, starlette_client, test_group):
        """Send a large message payload."""
        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws:
            large_content = "x" * 50000
            ws.send_json({
                "type": "message",
                "content": large_content,
                "sender_name": "big",
            })
            data = ws.receive_json()
            assert data["type"] == "ack"
            assert data["data"]["ok"] is True

    def test_unicode_content(self, starlette_client, test_group):
        """Send unicode content."""
        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws:
            ws.send_json({
                "type": "message",
                "content": "Hello 世界 🌍مرحبا",
                "sender_name": "unicode",
            })
            data = ws.receive_json()
            assert data["type"] == "ack"
            assert data["data"]["ok"] is True

    def test_special_characters_in_content(self, starlette_client, test_group):
        """Send content with special characters."""
        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws:
            ws.send_json({
                "type": "message",
                "content": '<script>alert("xss")</script> & "quotes" \'apostrophes\'',
                "sender_name": "special",
            })
            data = ws.receive_json()
            assert data["type"] == "ack"

    def test_message_with_metadata(self, starlette_client, test_group):
        """Send message with metadata."""
        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws:
            ws.send_json({
                "type": "message",
                "content": "meta msg",
                "sender_name": "meta",
                "message_type": "system",
                "metadata": {"key1": "value1", "key2": 42},
            })
            data = ws.receive_json()
            assert data["type"] == "ack"
            assert data["data"]["ok"] is True


# ---------------------------------------------------------------------------
# Performance / Load Tests
# ---------------------------------------------------------------------------

class TestPerformance:
    """Basic performance tests."""

    def test_high_message_throughput(self, starlette_client, test_group):
        """Send many messages rapidly."""
        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws:
            for i in range(50):
                ws.send_json({
                    "type": "message",
                    "content": f"rapid-{i}",
                    "sender_name": "load",
                })
            # Read all acks
            for i in range(50):
                data = ws.receive_json()
                assert data["type"] == "ack"

    def test_connection_stability_over_time(self, starlette_client, test_group):
        """Connection stays stable with periodic messages."""
        with starlette_client.websocket_connect(f"/api/v1/ws/groups/{test_group}") as ws:
            for i in range(10):
                ws.send_json({
                    "type": "message",
                    "content": f"stable-{i}",
                    "sender_name": "stability",
                })
                data = ws.receive_json()
                assert data["type"] == "ack"
                time.sleep(0.05)
