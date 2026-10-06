"""HTTP API 端到端测试（FastAPI TestClient + 确定性 demo 运行器）。"""

from __future__ import annotations

import os
import tempfile
import time

import agent_bootstrap  # noqa: F401
import pytest
from agent_system.api.routes import RunnerStore, RunRequest

_DATA_DIR = os.path.join(tempfile.gettempdir(), "taor_api_test")


def test_runner_store_flow() -> None:
    store = RunnerStore(data_dir=_DATA_DIR)
    info = store.start(RunRequest(objective="查询并按部门汇总", session_id="t-1"))
    assert info.state == "running"

    deadline = time.time() + 30
    while time.time() < deadline:
        cur = store.get("t-1")
        if cur is not None and cur.state == "done":
            break
        time.sleep(0.05)
    else:
        pytest.fail("任务未在超时内完成")

    assert cur is not None
    assert cur.state == "done"
    assert cur.result is not None
    assert cur.result["report"]["status"] == "completed"
    assert cur.result["report"]["tool_calls"] >= 1
    assert len(cur.result["events"]) > 0
    assert any(s["kind"] == "incremental" for s in cur.result["snapshots"])


def test_runner_store_unknown_session_404() -> None:
    store = RunnerStore(data_dir=_DATA_DIR)
    assert store.get("no-such-session") is None


def test_router_health_and_run() -> None:
    from agent_system.api.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        r = client.get("/api/agent/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

        created = client.post(
            "/api/agent/run",
            json={
                "objective": "查询并按部门汇总",
                "session_id": "http-1",
            },
        )
        assert created.status_code == 200
        assert created.json()["state"] == "running"

        deadline = time.time() + 30
        while time.time() < deadline:
            poll = client.get("/api/agent/session/http-1/poll")
            assert poll.status_code == 200
            if poll.json()["state"] == "done":
                break
            time.sleep(0.1)
        else:
            pytest.fail("HTTP 轮询未在超时内完成")

        payload = poll.json()
        assert payload["result"]["report"]["status"] == "completed"

        missing = client.get("/api/agent/session/nope")
        assert missing.status_code == 404
