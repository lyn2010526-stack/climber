"""End-to-end WebSocket endpoint tests for app/api/v1/generic.py.

Protocol notes (read from the endpoint implementations):
- /api/v1/ws/{session_id}        : send_text -> {"type":"echo","data":<text>}
- /api/v1/ws/task/{task_id}      : connect -> task_state snapshot; {"type":"ping"} -> {"type":"pong"}
- /api/v1/ws/groups/{group_id}   : message payload -> {"type":"ack"}; invalid JSON -> error
- /api/v1/ws/collab/{session_id} : ping/pong, hello, message broadcast, broadcast relay
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _create_group(client) -> str:
    resp = client.post("/api/v1/groups", json={"name": "WsGroup"})
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def test_ws_echo_connected_and_echoes(client):
    with client.websocket_connect("/api/v1/ws/sess-1?token=t1") as ws:
        welcome = ws.receive_json()
        assert welcome["type"] == "connected"
        assert welcome["session_id"] == "sess-1"
        ws.send_text("hello ws")
        assert ws.receive_json() == {"type": "echo", "data": "hello ws"}
        ws.send_text("second")
        assert ws.receive_json() == {"type": "echo", "data": "second"}


def test_ws_task_snapshot_for_existing_task(client):
    gid = _create_group(client)
    task = client.post("/api/v1/tasks", json={"group_id": gid, "description": "do it"}).json()
    with client.websocket_connect(f"/api/v1/ws/task/{task['id']}?token=t1") as ws:
        first = ws.receive_json()
        assert first["type"] == "task_state"
        payload = first["task"]
        assert payload["id"] == task["id"]
        assert payload["group_id"] == gid
        assert payload["status"] == "pending"
        assert "created_at" in payload
        assert "max_rounds" in payload
        ws.send_text(json.dumps({"type": "ping"}))
        assert ws.receive_json() == {"type": "pong"}


def test_ws_task_unknown_task_reports_error(client):
    with client.websocket_connect("/api/v1/ws/task/nonexistent-task?token=t1") as ws:
        first = ws.receive_json()
        assert first["type"] == "error"
        assert first["error"] == "task_not_found"
        assert first["task_id"] == "nonexistent-task"
        ws.send_text(json.dumps({"type": "ping"}))
        assert ws.receive_json() == {"type": "pong"}
        ws.send_text("not json")
        assert ws.receive_json()["error"] == "invalid_json"


def test_ws_group_not_found_closes(client):
    with client.websocket_connect("/api/v1/ws/groups/nonexistent-group?token=t1") as ws:
        assert ws.receive_json() == {"type": "error", "error": "group_not_found"}
        assert ws.receive()["type"] == "websocket.close"


def test_ws_group_ack_and_invalid_json(client):
    gid = _create_group(client)
    with client.websocket_connect(f"/api/v1/ws/groups/{gid}?token=t1") as ws:
        ws.send_text(json.dumps({"type": "message", "content": "hi", "sender_name": "alice"}))
        while True:
            frame = ws.receive_json()
            if frame.get("type") == "ack":
                break
        assert frame["data"]["ok"] is True
        ws.send_text("{not json")
        assert ws.receive_json() == {"type": "error", "error": "invalid_json"}


def test_ws_group_message_persists_with_agent_id(client):
    gid = _create_group(client)
    with client.websocket_connect(f"/api/v1/ws/groups/{gid}?token=t1") as ws:
        ws.send_text(json.dumps({"type": "message", "content": "from agent", "agent_id": "ag-1"}))
        while True:
            frame = ws.receive_json()
            if frame.get("type") == "ack":
                break
        assert frame["data"]["ok"] is True
    resp = client.get(f"/api/v1/groups/{gid}/messages")
    assert resp.status_code == 200, resp.text
    msgs = resp.json()["messages"]
    saved = [m for m in msgs if m.get("content") == "from agent"]
    assert saved, "message should be persisted via AgentGroupMessage"
    assert saved[0]["agent_id"] == "ag-1"


def test_ws_collab_hello_and_ping(client):
    with client.websocket_connect("/api/v1/ws/collab/c1?token=t1") as ws:
        ws.send_text(json.dumps({"type": "ping"}))
        assert ws.receive_json() == {"type": "pong"}
        ws.send_text(json.dumps({"type": "hello"}))
        assert ws.receive_json() == {"type": "hello", "session_id": "c1", "user_id": "default-user"}


def test_ws_collab_message_broadcast_and_unknown_type(client):
    with client.websocket_connect("/api/v1/ws/collab/c2?token=t1") as ws:
        ws.send_text(json.dumps({"type": "message", "content": "hello team"}))
        msg = ws.receive_json()
        assert msg["type"] == "message"
        assert msg["content"] == "hello team"
        assert msg["session_id"] == "c2"
        assert "ts" in msg
        ws.send_text(json.dumps({"type": "broadcast", "data": {"foo": "bar"}}))
        evt = ws.receive_json()
        assert evt["type"] == "collab_event"
        assert evt["data"]["foo"] == "bar"
        assert evt["data"]["session_id"] == "c2"
        ws.send_text(json.dumps({"type": "nope"}))
        err = ws.receive_json()
        assert err["error"] == "unknown_type"
        assert err["msg_type"] == "nope"


WS_PATHS = [
    "/api/v1/ws/sess-1",
    "/api/v1/ws/task/some-task",
    "/api/v1/ws/groups/some-group",
    "/api/v1/ws/collab/some-session",
]


@pytest.mark.parametrize("path", WS_PATHS)
def test_ws_without_token_rejected_4401(client, path):
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(path):
            pass
    assert exc_info.value.code == 4401


def test_ws_authorization_header_accepted(client):
    with client.websocket_connect(
        "/api/v1/ws/sess-1", headers={"Authorization": "Bearer abc"}
    ) as ws:
        assert ws.receive_json()["type"] == "connected"


def test_ws_sec_websocket_protocol_accepted(client):
    with client.websocket_connect(
        "/api/v1/ws/sess-1", headers={"Sec-WebSocket-Protocol": "Bearer, abc"}
    ) as ws:
        assert ws.receive_json()["type"] == "connected"
