"""Checkpoint durability.

``AgentEngine`` defaulted to ``InMemoryCheckpointStore``, so every restart threw
away all checkpoints and ``RecoveryManager`` had nothing to restore. The engine
now defaults to ``SQLiteCheckpointStore``; tests that need isolation still pass
an in-memory store explicitly.
"""

from __future__ import annotations

import pytest

from app.core.agent_engine import AgentEngine
from app.core.checkpoint import (
    CheckpointData,
    InMemoryCheckpointStore,
    SQLiteCheckpointStore,
)


def test_checkpoint_query_indexes_cover_recovery_ordering() -> None:
    from app.storage.database import CheckpointRecord

    indexes = {
        index.name: tuple(column.name for column in index.columns)
        for index in CheckpointRecord.__table__.indexes
    }

    assert indexes["ix_checkpoints_session_thread_iteration_created"] == (
        "session_id",
        "thread_id",
        "iteration",
        "created_at",
    )
    assert indexes["ix_checkpoints_session_thread_created"] == (
        "session_id",
        "thread_id",
        "created_at",
    )
    assert indexes["ix_checkpoints_session_created"] == ("session_id", "created_at")


@pytest.fixture
def engine():
    """A bare engine with isolated stores, skipping heavy subsystem setup."""
    instance = AgentEngine.__new__(AgentEngine)
    instance._checkpoints = InMemoryCheckpointStore()
    return instance


def test_default_store_is_persistent():
    engine = AgentEngine(model_registry=object(), tool_registry=object())
    assert isinstance(engine.checkpoint_store, SQLiteCheckpointStore), (
        "the engine must persist checkpoints by default, or a restart loses them"
    )


def test_explicit_in_memory_store_is_respected():
    store = InMemoryCheckpointStore()
    engine = AgentEngine(
        model_registry=object(), tool_registry=object(), checkpoint_store=store
    )
    assert engine.checkpoint_store is store


async def test_sqlite_store_survives_a_new_store_instance():
    store = SQLiteCheckpointStore()
    checkpoint = CheckpointData(
        session_id="durable-1",
        messages=[{"role": "user", "content": "remember me"}],
        iteration=3,
        status="running",
    )
    await store.save(None, checkpoint, checkpoint_id="cp-durable-1")

    # A second store object stands in for a restarted process.
    reopened = SQLiteCheckpointStore()
    found = await reopened.get_latest(None, "durable-1")

    assert found is not None
    recovered, checkpoint_id = found
    assert checkpoint_id == "cp-durable-1"
    assert recovered.messages == [{"role": "user", "content": "remember me"}]
    assert recovered.iteration == 3


async def test_recovery_manager_reads_the_persistent_store():
    from app.core.recovery import RecoveryManager

    store = SQLiteCheckpointStore()
    await store.save(
        None,
        CheckpointData(
            session_id="recover-1",
            messages=[{"role": "user", "content": "go"}],
            iteration=1,
            status="running",
        ),
        checkpoint_id="cp-recover-1",
    )

    recovered = await RecoveryManager(store).recover_session("recover-1")

    assert recovered is not None
    assert recovered["session_id"] == "recover-1"


async def test_recovery_after_restart_preserves_replay_safety():
    """A restarted recovery manager must retain the safe/withheld split."""
    from app.core.recovery import RecoveryManager

    session_id = "recover-restart-durable"
    store = SQLiteCheckpointStore()
    await store.save(
        None,
        CheckpointData(
            session_id=session_id,
            messages=[
                {"role": "user", "content": "continue"},
                {"role": "tool", "tool_call_id": "write-1", "content": "wrote"},
            ],
            iteration=4,
            status="interrupted",
            tool_results=[
                {"tool": "read_file", "tool_call_id": "read-1", "result": "stable"},
                {"tool": "write_file", "tool_call_id": "write-1", "result": "wrote"},
            ],
        ),
        checkpoint_id="cp-restart-replay-safety",
    )

    recovered = await RecoveryManager(SQLiteCheckpointStore()).recover_session(session_id)

    assert recovered is not None
    assert [entry["tool"] for entry in recovered["tool_results"]] == ["read_file"]
    assert [entry["tool"] for entry in recovered["withheld_tool_results"]] == ["write_file"]
    assert recovered["messages"][-1] == {
        "role": "tool",
        "content": "stable",
        "tool_call_id": "read-1",
    }
    assert all(message.get("tool_call_id") != "write-1" for message in recovered["messages"])
