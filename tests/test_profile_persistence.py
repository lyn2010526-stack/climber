"""Tests for the persisted profile loop (ProfileStore + repositories)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.profile import router as profile_router
from app.core.profile.persistence import ProfileStore
from app.storage import async_session
from app.storage.repository_user_profile import get_snapshot, list_events, upsert_snapshot


def _user() -> str:
    return str(uuid.uuid4())


def _client():
    app = FastAPI()
    app.include_router(profile_router, prefix="/profile")
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_record_then_summary_reflects_event() -> None:
    user = _user()
    store = ProfileStore()
    await store.record_event(
        user,
        instruction="refactor the storage layer",
        task_type="refactor",
        outcome="success",
    )
    summary = await store.summary(user)
    assert summary.enabled is True
    assert summary.success_rate == 1.0
    assert summary.task_preferences.get("refactor", 0.0) > 0.0
    assert summary.prompt_hints


async def test_record_run_persists_run_outcome() -> None:
    user = _user()
    store = ProfileStore()
    await store.record_run(user, instruction="fix the login bug", outcome="success")
    await store.record_run(user, instruction="retry deploy", outcome="failure", retried=True)
    summary = await store.summary(user)
    assert summary.success_rate == pytest.approx(0.5)
    assert summary.retry_rate == pytest.approx(0.5)


async def test_summary_replays_from_database_not_memory() -> None:
    user = _user()
    store = ProfileStore()
    await store.record_event(
        user,
        instruction="ship the release",
        task_type="coding",
        outcome="failure",
        feedback="negative",
        retried=True,
    )
    async with async_session() as db:
        rows = await list_events(db, user)
        assert len(rows) == 1
        assert rows[0].task_type == "coding"
        assert rows[0].retried is True
        assert rows[0].source == "agent_internal"

    rebuilt = ProfileStore()
    summary = await rebuilt.summary(user)
    assert summary.success_rate == 0.0
    assert summary.retry_rate == 1.0


async def test_snapshot_is_persisted_and_readable() -> None:
    user = _user()
    store = ProfileStore()
    await store.record_event(
        user,
        instruction="ship the release",
        task_type="coding",
        outcome="failure",
        feedback="negative",
    )
    summary = await store.summary(user)
    async with async_session() as db:
        snapshot = await get_snapshot(db, user)
        assert snapshot is not None
        assert snapshot.confidence == pytest.approx(summary.confidence)
        assert snapshot.payload["success_rate"] == summary.success_rate
        assert snapshot.payload["task_preferences"] == summary.task_preferences
        assert snapshot.payload["retry_rate"] == summary.retry_rate


async def test_summary_snapshot_blends_with_previous_snapshot() -> None:
    user = _user()
    store = ProfileStore()
    await store.record_event(user, instruction="ship", task_type="coding", outcome="success")
    first = await store.summary(user)
    await store.record_event(user, instruction="review", task_type="review", outcome="failure")
    second = await store.summary(user)
    assert second.success_rate == pytest.approx(first.success_rate * 0.7 + 0.5 * 0.3)
    assert second.task_preferences["coding"] > 0.0
    assert second.task_preferences["review"] > 0.0


async def test_upsert_snapshot_folds_into_one_row() -> None:
    user = _user()
    async with async_session() as db:
        first = await upsert_snapshot(db, user_id=user, payload={"v": 1}, confidence=0.1)
        second = await upsert_snapshot(db, user_id=user, payload={"v": 2}, confidence=0.2)
        await db.commit()
        assert first.user_id == second.user_id
        reread = await get_snapshot(db, user)
        assert reread is not None
        assert reread.payload == {"v": 2}
        assert reread.confidence == pytest.approx(0.2)


async def test_purchase_history_source_is_rejected_without_write() -> None:
    user = _user()
    store = ProfileStore()
    with pytest.raises(ValueError, match="source must be one of"):
        await store.record_event(
            user,
            instruction="mine my purchase history",
            task_type="coding",
            outcome="success",
            source="purchase_history",
        )
    async with async_session() as db:
        assert await list_events(db, user) == []


async def test_summary_for_unknown_user_is_empty() -> None:
    store = ProfileStore()
    summary = await store.summary(_user())
    assert summary.confidence == 0.0
    assert summary.success_rate == 0.0
    assert summary.task_preferences == {}


async def test_list_events_honors_occurred_after() -> None:
    user = _user()
    store = ProfileStore()
    await store.record_event(user, instruction="first pass", task_type="coding", outcome="success")
    cutoff = datetime.now(UTC)
    await store.record_event(user, instruction="second pass", task_type="review", outcome="failure")
    async with async_session() as db:
        all_rows = await list_events(db, user)
        later = await list_events(db, user, occurred_after=cutoff)
    assert len(all_rows) == 2
    assert [r.task_type for r in later] == ["review"]


# --- HTTP contract ---


async def test_api_event_then_summary_and_suggestions() -> None:
    async with _client() as client:
        created = await client.post(
            "/profile/events",
            json={
                "instruction": "refactor the api layer",
                "task_type": "refactor",
                "outcome": "success",
                "tool": "grep",
            },
        )
        assert created.status_code == 200, created.text
        body = created.json()
        assert body["user_id"] == "default-user"
        assert body["source"] == "agent_internal"
        assert body["outcome"] == "success"

        summary = await client.get("/profile/summary")
        suggestions = await client.get(
            "/profile/suggestions", params={"current_instruction": "tidy the imports"}
        )

    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["success_rate"] == 1.0
    assert summary_body["task_preferences"].get("refactor", 0.0) > 0.0
    assert summary_body["enabled"] is True

    assert suggestions.status_code == 200
    hints = suggestions.json()
    assert hints["current_instruction"] == "tidy the imports"
    assert hints["profile_may_not_override_current_instruction"] is True
    assert hints["enabled"] is True


async def test_api_rejects_purchase_history_source_with_400() -> None:
    async with _client() as client:
        response = await client.post(
            "/profile/events",
            json={
                "instruction": "mine my purchase history",
                "task_type": "coding",
                "outcome": "success",
                "source": "purchase_history",
            },
        )
    assert response.status_code == 400
    assert "source must be one of" in response.json()["detail"]


async def test_api_rejects_empty_instruction() -> None:
    async with _client() as client:
        response = await client.post(
            "/profile/events",
            json={"instruction": "", "task_type": "coding", "outcome": "success"},
        )
    assert response.status_code == 422
