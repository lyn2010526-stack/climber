"""Focused checkpoint persistence and session recovery tests."""

from __future__ import annotations

import asyncio
import json

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.checkpoint import CheckpointData, PendingWrite, SQLiteCheckpointStore
from app.core.recovery import RecoveryManager
from app.core.session import AgentSession, SessionConfig
from app.core.task_state_machine import TaskState
from app.storage.database import ensure_checkpoint_schema


@pytest.mark.asyncio
async def test_checkpoint_full_field_roundtrip_and_session_isolation() -> None:
    store = SQLiteCheckpointStore()
    checkpoint = CheckpointData(
        session_id="persist-a",
        messages=[{"role": "user", "content": "hello"}],
        iteration=3,
        status="processing",
        tool_results=[{"tool_name": "echo", "result": "ok"}],
        metadata={"request": "one"},
        channel_values={"messages": ["hello"], "nested": {"ok": True}},
        channel_versions={"messages": 3},
        versions_seen={"agent": {"messages": 2}},
        pending_writes=[
            PendingWrite(channel="messages", value="next", write_id="write-1")
        ],
    )
    await store.save(None, checkpoint, thread_id="turn-a", checkpoint_id="full-a")
    await store.save(
        None,
        CheckpointData("persist-b", [], 99, "completed"),
        thread_id="turn-b",
        checkpoint_id="full-b",
    )

    loaded = await store.get(None, "full-a")
    assert loaded is not None
    assert loaded.channel_values == checkpoint.channel_values
    assert loaded.channel_versions == checkpoint.channel_versions
    assert loaded.versions_seen == checkpoint.versions_seen
    assert loaded.pending_writes == checkpoint.pending_writes
    assert loaded.tool_results == checkpoint.tool_results
    assert loaded.metadata["thread_id"] == "turn-a"

    latest = await store.get_latest(None, "persist-a")
    assert latest is not None
    assert latest[1] == "full-a"
    assert await store.list_for_session(None, "persist-a") == ["full-a"]


def test_old_checkpoint_record_uses_safe_defaults() -> None:
    record = type(
        "OldCheckpoint",
        (),
        {
            "session_id": "legacy",
            "messages": "[]",
            "iteration": 1,
            "status": "running",
            "tool_results": "[]",
            "metadata_": json.dumps(
                {
                    "pending_writes": [
                        {
                            "channel": "legacy",
                            "value": 1,
                            "write_id": "old-write",
                            "status": "pending",
                        }
                    ]
                }
            ),
        },
    )()

    checkpoint = SQLiteCheckpointStore()._to_checkpoint(record)
    assert checkpoint.channel_values == {}
    assert checkpoint.channel_versions == {}
    assert checkpoint.versions_seen == {}
    assert checkpoint.pending_writes[0].write_id == "old-write"


@pytest.mark.asyncio
async def test_schema_helper_upgrades_an_existing_legacy_table() -> None:
    legacy_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with legacy_engine.begin() as connection:
        await connection.execute(
            text(
                "CREATE TABLE checkpoints ("
                "id TEXT PRIMARY KEY, session_id TEXT NOT NULL, "
                "thread_id TEXT NOT NULL, messages TEXT NOT NULL, "
                "iteration INTEGER NOT NULL, status TEXT NOT NULL, "
                "tool_results TEXT, metadata TEXT, parent_id TEXT, created_at DATETIME)"
            )
        )

    await ensure_checkpoint_schema(legacy_engine)

    async with legacy_engine.connect() as connection:
        result = await connection.execute(text("PRAGMA table_info(checkpoints)"))
        names = {row[1] for row in result.all()}
    assert {
        "channel_values",
        "channel_versions",
        "versions_seen",
        "pending_writes",
    }.issubset(names)
    await legacy_engine.dispose()


@pytest.mark.asyncio
async def test_session_snapshot_roundtrip_excludes_runtime_primitives() -> None:
    session = AgentSession(
        SessionConfig(
            session_id="snapshot-session",
            agent_id="agent",
            user_id="user",
            provider="openai",
            model_id="model",
            api_key="secret",
            max_iterations=7,
        )
    )
    session.messages = [{"role": "assistant", "content": "saved"}]
    session._last_iteration = 4
    session._last_error = "temporary"
    session._stop_requested = True
    session.tool_results = [{"tool_name": "echo", "result": "saved"}]
    session.state_machine._state = TaskState.FAILED
    session._pending_tasks.add(asyncio.create_task(asyncio.sleep(0)))

    snapshot = session.snapshot()
    encoded = json.dumps(snapshot)
    restored = AgentSession.from_snapshot(json.loads(encoded), api_key="replacement")

    assert "secret" not in encoded
    assert restored.api_key == "replacement"
    assert restored.messages == session.messages
    assert restored._last_iteration == 4
    assert restored.status.value == "failed"
    assert restored._stop_requested is True
    assert restored._last_error == "temporary"
    assert restored.tool_results == session.tool_results
    assert restored._pending_tasks == set()
    await session._await_pending_tasks()


@pytest.mark.asyncio
async def test_recovery_restores_execution_state_and_resume_intent() -> None:
    store = SQLiteCheckpointStore()
    checkpoint = CheckpointData(
        session_id="recover-session",
        messages=[{"role": "tool", "content": "result"}],
        iteration=5,
        status="processing",
        tool_results=[{"tool_name": "lookup", "result": "result"}],
        channel_values={"last_tool_results": ["result"]},
    )
    await store.save(None, checkpoint, checkpoint_id="recover-checkpoint")
    session = AgentSession(SessionConfig(session_id="recover-session"))

    restored = await RecoveryManager(store).restore_session(session)

    assert restored is True
    assert session.messages == checkpoint.messages
    assert session._last_iteration == 5
    assert session.status.value == "running"
    assert session.tool_results == checkpoint.tool_results
    assert session._resume_interrupted is True


@pytest.mark.asyncio
async def test_final_checkpoint_is_history_for_a_new_turn() -> None:
    store = SQLiteCheckpointStore()
    checkpoint = CheckpointData(
        session_id="completed-session",
        messages=[{"role": "assistant", "content": "done"}],
        iteration=2,
        status="processing",
        channel_values={"final_result": "done"},
    )
    await store.save(None, checkpoint, checkpoint_id="completed-checkpoint")
    session = AgentSession(SessionConfig(session_id="completed-session"))

    await RecoveryManager(store).restore_session(session)

    assert session.messages == checkpoint.messages
    assert session._last_iteration == 2
    assert session.status.value == "completed"
    assert session._resume_interrupted is False
