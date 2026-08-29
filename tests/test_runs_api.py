"""Tests for the Run management endpoints (app.api.v1.runs)."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

os.environ["APP_TESTING"] = "true"
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/e2e.db")

from fastapi.testclient import TestClient

from app.core.run_protocol import InMemoryRunStore, RunRecord, RunStatus
from app.main import app


class _FakeAdapter:
    def __init__(self) -> None:
        self.store = InMemoryRunStore()
        self.replayed: list[dict] = []
        self.cancelled: list[str] = []
        self.resumed: list[str] = []

    async def require_run(self, run_id: str) -> RunRecord:
        return await self.store.require(run_id)

    async def list_runs(self, **kwargs):
        return await self.store.list_runs(**kwargs)

    async def replay(self, run_id: str, after: int = 0, limit: int = 256):
        page = await self.store.list_events(run_id, after=after, limit=limit)
        self.replayed.append(run_id)
        return page

    async def cancel(self, run_id: str, actor_id: str) -> RunRecord:
        self.cancelled.append(run_id)
        return await self.store.transition(run_id, RunStatus.RUNNING, RunStatus.CANCELLED)

    async def resume(self, command) -> object:
        self.resumed.append(command.run_id)
        return type(
            "Handle",
            (),
            {
                "run_id": command.run_id,
                "session_id": command.session_id,
                "status": RunStatus.RUNNING,
            },
        )()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def fake_adapter():
    return _FakeAdapter()


def _fake_run(**kwargs) -> RunRecord:
    return RunRecord(user_id="default-user", **kwargs)


def _install(fake_adapter):
    return patch(
        "app.api.v1.runs.get_run_adapter",
        return_value=fake_adapter,
    )


def test_get_run_returns_state_and_messages(fake_adapter, client):
    run = _fake_run(run_id="run-1", session_id="session-1")
    import asyncio

    asyncio.get_event_loop().run_until_complete(fake_adapter.store.create(run))

    with _install(fake_adapter):
        resp = client.get("/api/v1/runs/run-1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_id"] == "run-1"
    assert body["status"] == "pending"
    assert body["messages"] == []


def test_get_run_returns_404_for_missing(fake_adapter, client):
    with _install(fake_adapter):
        resp = client.get("/api/v1/runs/does-not-exist")
    assert resp.status_code == 404


def test_list_runs_filters_and_paginates(fake_adapter, client):
    import asyncio

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        fake_adapter.store.create(
            _fake_run(run_id="run-a", session_id="session-1")
        )
    )
    loop.run_until_complete(
        fake_adapter.store.create(
            _fake_run(run_id="run-b", session_id="session-2")
        )
    )

    with _install(fake_adapter):
        resp = client.get("/api/v1/runs", params={"session_id": "session-1"})
    assert resp.status_code == 200
    body = resp.json()
    assert [item["run_id"] for item in body["items"]] == ["run-a"]
    assert body["total"] == 1
    assert body["has_more"] is False


def test_get_run_events_replays_stream(fake_adapter, client):
    import asyncio

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        fake_adapter.store.create(
            _fake_run(run_id="run-1", session_id="session-1")
        )
    )
    from datetime import UTC, datetime

    from app.core.run_protocol import RunEvent

    loop.run_until_complete(
        fake_adapter.store.append_event(
            RunEvent(
                event_id="event-1",
                run_id="run-1",
                sequence=None,
                event_type="text",
                data={"content": "hello"},
                created_at=datetime.now(UTC),
            )
        )
    )

    with _install(fake_adapter):
        resp = client.get("/api/v1/runs/run-1/events")
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_id"] == "run-1"
    assert body["events"][0]["event"] == "text"
    assert fake_adapter.replayed == ["run-1"]


def test_cancel_run_transitions_to_cancelled(fake_adapter, client):
    import asyncio

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        fake_adapter.store.create(
            _fake_run(run_id="run-1", session_id="session-1")
        )
    )
    loop.run_until_complete(
        fake_adapter.store.transition("run-1", RunStatus.PENDING, RunStatus.RUNNING)
    )

    with _install(fake_adapter):
        resp = client.post("/api/v1/runs/run-1/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
    assert fake_adapter.cancelled == ["run-1"]


def test_cancel_missing_run_returns_404(fake_adapter, client):
    with _install(fake_adapter):
        resp = client.post("/api/v1/runs/nope/cancel")
    assert resp.status_code == 404


def test_resume_run_returns_handle(fake_adapter, client):
    import asyncio

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        fake_adapter.store.create(
            _fake_run(run_id="run-1", session_id="session-1")
        )
    )
    loop.run_until_complete(
        fake_adapter.store.transition("run-1", RunStatus.PENDING, RunStatus.RUNNING)
    )
    loop.run_until_complete(
        fake_adapter.store.transition("run-1", RunStatus.RUNNING, RunStatus.PAUSED)
    )

    with _install(fake_adapter):
        resp = client.post("/api/v1/runs/run-1/resume")
    assert resp.status_code == 200, resp.text
    assert resp.json()["run_id"] == "run-1"
    assert fake_adapter.resumed == ["run-1"]
