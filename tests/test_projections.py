"""Tests for event-stream projections."""

from __future__ import annotations

import pytest

from app.core.integration.event_store import EventStore
from app.core.integration.projections import (
    project_session,
    project_skill_usage,
    project_stats,
    project_trajectory,
)


async def _seed(store: EventStore, stream: str = "s1") -> None:
    await store.append("session_state", {"from": "pending", "to": "processing"}, stream_id=stream)
    await store.append("message", {"role": "user", "content": "hi", "tokens": 2}, stream_id=stream)
    await store.append("thinking", {"iteration": 1}, stream_id=stream)
    await store.append("tool_call", {"name": "read_file", "arguments": {"path": "a"}}, stream_id=stream)
    await store.append("tool_result", {"tool_name": "read_file", "success": True}, stream_id=stream)
    await store.append("skill_load", {"skill_id": "web", "level": 2}, stream_id=stream)
    await store.append(
        "message", {"role": "assistant", "content": "done", "tokens": 5}, stream_id=stream
    )
    await store.append("done", {"status": "completed", "iterations": 1, "tokens_used": 7}, stream_id=stream)
    await store.append(
        "session_state", {"from": "processing", "to": "completed"}, stream_id=stream
    )


@pytest.mark.asyncio
async def test_project_session_rebuilds_state(tmp_path):
    store = EventStore(tmp_path / "events.db")
    try:
        await _seed(store)
        state = await project_session(store, "s1")

        assert state["status"] == "completed"
        assert state["message_count"] == 2
        assert state["tool_calls"] == 1
        assert state["iterations"] == 1
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_project_session_empty_stream(tmp_path):
    store = EventStore(tmp_path / "events.db")
    try:
        state = await project_session(store, "missing")
        assert state["status"] is None
        assert state["message_count"] == 0
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_project_trajectory_returns_ordered_timeline(tmp_path):
    store = EventStore(tmp_path / "events.db")
    try:
        await _seed(store)
        trajectory = await project_trajectory(store, "s1")

        types = [step["event_type"] for step in trajectory]
        assert types == [
            "thinking",
            "tool_call",
            "tool_result",
            "done",
        ]
        assert trajectory[0]["sequence"] < trajectory[-1]["sequence"]
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_project_stats_aggregates_counts_and_tokens(tmp_path):
    store = EventStore(tmp_path / "events.db")
    try:
        await _seed(store)
        await store.append("tool_call", {"name": "read_file"}, stream_id="s2")
        await store.append("tool_call", {"name": "write_file"}, stream_id="s2")

        stats = await project_stats(store)

        assert stats["messages"] == 2
        assert stats["tool_calls_total"] == 3
        assert stats["tool_calls_by_name"] == {"read_file": 2, "write_file": 1}
        assert stats["tokens"] == 7

        s1_stats = await project_stats(store, session_id="s1")
        assert s1_stats["tool_calls_total"] == 1
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_project_skill_usage_counts_loads(tmp_path):
    store = EventStore(tmp_path / "events.db")
    try:
        await _seed(store)
        await store.append("skill_load", {"skill_id": "web", "level": 3}, stream_id="s1")
        await store.append("skill_load", {"skill_id": "shell", "level": 1}, stream_id="s1")

        usage = await project_skill_usage(store, "s1")
        assert usage == {"web": 2, "shell": 1}
    finally:
        await store.close()
