"""Channel-level durability tests for the SQLite checkpoint store.

These tests prove that the Climber checkpoint store survives process restarts
and preserves the LangGraph-style channel snapshots required for accurate
recovery semantics. They do not touch permissions, MCP registration, or
sandbox configuration.
"""

from __future__ import annotations

import pytest

from app.core.agent_engine import AgentEngine, AgentSession
from app.core.checkpoint import (
    CheckpointData,
    InMemoryCheckpointStore,
    PendingWrite,
    SQLiteCheckpointStore,
)


@pytest.mark.asyncio
async def test_checkpoint_save_round_trips_channel_snapshots():
    store = SQLiteCheckpointStore()
    cp = CheckpointData(
        session_id="sess-channel",
        messages=[{"role": "user", "content": "hi"}],
        iteration=2,
        status="processing",
        channel_values={
            "last_tool_calls": [{"id": "call-1", "name": "echo"}],
            "context_tokens": 128,
        },
        channel_versions={"messages": 2, "tools": 1},
        versions_seen={"node": {"messages": 2, "tools": 1}},
        pending_writes=[PendingWrite(channel="messages", value={"role": "assistant", "content": "ok"}, write_id="w-1")],
    )

    cid = await store.save(None, cp, thread_id="turn-channel", checkpoint_id="cp-channel-1")

    loaded = await store.get(None, cid)
    assert loaded is not None
    assert loaded.channel_values == {
        "last_tool_calls": [{"id": "call-1", "name": "echo"}],
        "context_tokens": 128,
    }
    assert loaded.channel_versions == {"messages": 2, "tools": 1}
    assert loaded.versions_seen == {"node": {"messages": 2, "tools": 1}}
    assert loaded.pending_writes and loaded.pending_writes[0].write_id == "w-1"
    assert "channel_values" not in loaded.metadata
    assert "channel_versions" not in loaded.metadata


@pytest.mark.asyncio
async def test_checkpoint_save_is_idempotent_under_same_id():
    store = SQLiteCheckpointStore()
    cp_v1 = CheckpointData(
        session_id="sess-upsert",
        messages=[],
        iteration=1,
        status="processing",
        channel_values={"k": "first"},
    )
    await store.save(None, cp_v1, thread_id="turn-upsert", checkpoint_id="cp-upsert-stable")

    cp_v2 = CheckpointData(
        session_id="sess-upsert",
        messages=[{"role": "assistant", "content": "x"}],
        iteration=2,
        status="completed",
        channel_values={"k": "second"},
        channel_versions={"messages": 2},
    )
    cid = await store.save(None, cp_v2, thread_id="turn-upsert", checkpoint_id="cp-upsert-stable")

    loaded = await store.get(None, cid)
    assert loaded is not None
    assert loaded.iteration == 2
    assert loaded.status == "completed"
    assert loaded.channel_values == {"k": "second"}
    assert loaded.channel_versions == {"messages": 2}


@pytest.mark.asyncio
async def test_put_writes_dedupes_by_write_id():
    store = SQLiteCheckpointStore()
    cp = CheckpointData(
        session_id="sess-writes",
        messages=[],
        iteration=1,
        status="processing",
    )
    cid = await store.save(None, cp, thread_id="turn-writes", checkpoint_id="cp-writes-1")

    pending = PendingWrite(channel="messages", value={"role": "user", "content": "again"}, write_id="dup-1")
    await store.put_writes(cid, [pending])
    await store.put_writes(cid, [pending])

    writes = await store.get_writes(cid)
    assert len(writes) == 1
    assert writes[0].write_id == "dup-1"


@pytest.mark.asyncio
async def test_get_latest_returns_most_recent_iteration():
    store = SQLiteCheckpointStore()
    for iteration in (1, 2, 3):
        cp = CheckpointData(
            session_id="sess-latest",
            messages=[],
            iteration=iteration,
            status="processing",
        )
        await store.save(
            None,
            cp,
            thread_id="turn-latest",
            checkpoint_id=f"cp-latest-{iteration}",
        )

    latest = await store.get_latest(None, "sess-latest", thread_id="turn-latest")
    assert latest is not None
    cp, cid = latest
    assert cp.iteration == 3
    assert cid == "cp-latest-3"


@pytest.mark.asyncio
@pytest.mark.parametrize("store", [InMemoryCheckpointStore(), SQLiteCheckpointStore()])
async def test_get_latest_scopes_results_to_requested_turn(store):
    older_turn = CheckpointData(
        session_id="sess-turn-scope",
        messages=[],
        iteration=5,
        status="completed",
    )
    requested_turn = CheckpointData(
        session_id="sess-turn-scope",
        messages=[],
        iteration=1,
        status="processing",
    )
    await store.save(
        None,
        older_turn,
        thread_id="turn-older",
        checkpoint_id="cp-turn-older",
    )
    await store.save(
        None,
        requested_turn,
        thread_id="turn-requested",
        checkpoint_id="cp-turn-requested",
    )

    latest = await store.get_latest(
        None,
        "sess-turn-scope",
        thread_id="turn-requested",
    )

    assert latest is not None
    checkpoint, checkpoint_id = latest
    assert checkpoint.iteration == 1
    assert checkpoint.metadata["thread_id"] == "turn-requested"
    assert checkpoint_id == "cp-turn-requested"


@pytest.mark.asyncio
@pytest.mark.parametrize("store", [InMemoryCheckpointStore(), SQLiteCheckpointStore()])
async def test_get_latest_without_turn_returns_most_recently_saved_turn(store):
    older_turn = CheckpointData(
        session_id="sess-session-latest",
        messages=[],
        iteration=5,
        status="completed",
    )
    newer_turn = CheckpointData(
        session_id="sess-session-latest",
        messages=[],
        iteration=1,
        status="processing",
    )
    await store.save(
        None,
        older_turn,
        thread_id="turn-older",
        checkpoint_id="cp-session-older",
    )
    await store.save(
        None,
        newer_turn,
        thread_id="turn-newer",
        checkpoint_id="cp-session-newer",
    )

    latest = await store.get_latest(None, "sess-session-latest")

    assert latest is not None
    checkpoint, checkpoint_id = latest
    assert checkpoint.iteration == 1
    assert checkpoint.metadata["thread_id"] == "turn-newer"
    assert checkpoint_id == "cp-session-newer"


def test_checkpoint_id_uses_current_turn_id():
    session = AgentSession(
        session_id="11111111-1111-1111-1111-111111111111",
        agent_id="agent",
        user_id="user",
        provider="fake",
        model_id="fake-model",
        api_key="fake-key",
    )

    session.current_turn_id = "22222222-2222-2222-2222-222222222222"
    first_id = AgentEngine._checkpoint_id(session, 1)
    session.current_turn_id = "33333333-3333-3333-3333-333333333333"
    second_id = AgentEngine._checkpoint_id(session, 1)

    session.current_turn_id = "22222222-2222-2222-2222-222222222222"
    assert AgentEngine._checkpoint_id(session, 1) == first_id
    assert first_id != second_id
    assert len(first_id) <= 36
    assert len(second_id) <= 36
