"""Checkpoint rollback across both stores + RecoveryManager wiring.

Covers:
- InMemoryCheckpointStore.rollback_to returns the target snapshot and, with
  prune_descendants, drops checkpoints descending from it.
- SQLiteCheckpointStore.rollback_to parity: parent links come from record
  metadata, so descendant pruning must walk those chains.
- RecoveryManager.rollback_session / rollback_and_restore make the previously
  production-less rollback_to reachable, and refuse a checkpoint that belongs
  to a different session.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.checkpoint import CheckpointData, InMemoryCheckpointStore, SQLiteCheckpointStore
from app.core.recovery import RecoveryManager


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _cp(session_id: str, iteration: int, marker: str) -> CheckpointData:
    return CheckpointData(
        session_id=session_id,
        messages=[{"role": "user", "content": marker}],
        iteration=iteration,
        status="running",
        tool_results=[],
        metadata={},
        channel_values={},
        channel_versions={},
        versions_seen={},
        pending_writes=[],
    )


# ─── InMemory store ─────────────────────────────────────────────────────────


def test_inmemory_rollback_returns_target_snapshot() -> None:
    store = InMemoryCheckpointStore()
    first = _run(store.save(None, _cp("s1", 1, "first"), thread_id="t1"))
    _run(store.save(None, _cp("s1", 2, "second"), thread_id="t1", checkpoint_id="cp2", parent_id=first))

    target = _run(store.rollback_to(first))
    assert target is not None
    assert target.messages[0]["content"] == "first"
    # non-pruning rollback keeps descendants
    assert _run(store.get(None, "cp2")) is not None


def test_inmemory_rollback_prunes_descendants() -> None:
    store = InMemoryCheckpointStore()
    first = _run(store.save(None, _cp("s1", 1, "first"), thread_id="t1"))
    _run(store.save(None, _cp("s1", 2, "second"), thread_id="t1", checkpoint_id="cp2", parent_id=first))
    _run(store.save(None, _cp("s1", 3, "third"), thread_id="t1", checkpoint_id="cp3", parent_id="cp2"))
    # an independent checkpoint that must survive pruning
    other = _run(store.save(None, _cp("s1", 9, "other-branch"), thread_id="t2", checkpoint_id="cp-other"))

    target = _run(store.rollback_to(first, prune_descendants=True))
    assert target is not None
    assert _run(store.get(None, "cp2")) is None
    assert _run(store.get(None, "cp3")) is None
    assert _run(store.get(None, other)) is not None


def test_inmemory_rollback_unknown_returns_none() -> None:
    store = InMemoryCheckpointStore()
    assert _run(store.rollback_to("nope")) is None


# ─── SQLite store ───────────────────────────────────────────────────────────


def _wipe_checkpoints(session_id: str) -> None:
    from sqlalchemy import delete

    from app.storage import async_session
    from app.storage.database import CheckpointRecord, ensure_checkpoint_schema

    async def _inner() -> None:
        await ensure_checkpoint_schema()
        async with async_session() as db:
            await db.execute(delete(CheckpointRecord).where(CheckpointRecord.session_id == session_id))
            await db.commit()

    _run(_inner())


def test_sqlite_rollback_prunes_descendants() -> None:
    store = SQLiteCheckpointStore()
    sid = "rb-sqlite-1"
    _wipe_checkpoints(sid)
    try:
        first = _run(store.save(None, _cp(sid, 1, "first"), thread_id="t1", checkpoint_id="s1c1", parent_id=None))
        _run(store.save(None, _cp(sid, 2, "second"), thread_id="t1", checkpoint_id="s1c2", parent_id=first))
        _run(store.save(None, _cp(sid, 3, "third"), thread_id="t1", checkpoint_id="s1c3", parent_id="s1c2"))
        _run(store.save(None, _cp(sid, 9, "other"), thread_id="t2", checkpoint_id="s1cX", parent_id=None))

        target = _run(store.rollback_to("s1c1", prune_descendants=True))
        assert target is not None
        assert target.messages[0]["content"] == "first"
        assert _run(store.get(None, "s1c2")) is None
        assert _run(store.get(None, "s1c3")) is None
        assert _run(store.get(None, "s1cX")) is not None
    finally:
        _wipe_checkpoints(sid)


def test_sqlite_rollback_keeps_descendants_without_prune() -> None:
    store = SQLiteCheckpointStore()
    sid = "rb-sqlite-2"
    _wipe_checkpoints(sid)
    try:
        first = _run(store.save(None, _cp(sid, 1, "first"), thread_id="t1", checkpoint_id="s2c1", parent_id=None))
        _run(store.save(None, _cp(sid, 2, "second"), thread_id="t1", checkpoint_id="s2c2", parent_id=first))
        _run(store.rollback_to("s2c1"))
        assert _run(store.get(None, "s2c2")) is not None
    finally:
        _wipe_checkpoints(sid)


def test_sqlite_rollback_unknown_returns_none() -> None:
    store = SQLiteCheckpointStore()
    assert _run(store.rollback_to("nope-sqlite")) is None


# ─── RecoveryManager wiring (makes rollback_to production-reachable) ────────


def test_recovery_manager_rollback_session_payload_shape() -> None:
    store = InMemoryCheckpointStore()
    first = _run(store.save(None, _cp("s9", 1, "first"), thread_id="t1"))
    _run(store.save(None, _cp("s9", 2, "second"), thread_id="t1", checkpoint_id="cp-b", parent_id=first))
    manager = RecoveryManager(store)

    rolled = _run(manager.rollback_session("s9", first, prune_descendants=True))
    assert rolled is not None
    assert rolled["session_id"] == "s9"
    assert rolled["iteration"] == 1
    assert rolled["checkpoint_id"] == first
    assert rolled["messages"][0]["content"] == "first"
    assert _run(store.get(None, "cp-b")) is None
    # recover_session now returns the rollback point as latest
    latest = _run(manager.recover_session("s9"))
    assert latest is not None and latest["iteration"] == 1


def test_recovery_manager_rollback_rejects_foreign_session() -> None:
    store = InMemoryCheckpointStore()
    other = _run(store.save(None, _cp("s-other", 1, "foreign"), thread_id="t1"))
    manager = RecoveryManager(store)
    assert _run(manager.rollback_session("s-mine", other)) is None


def test_recovery_manager_rollback_and_restore_loads_session() -> None:
    from app.core.session import AgentSession

    store = InMemoryCheckpointStore()
    first = _run(store.save(None, _cp("s10", 1, "first-message"), thread_id="t1"))
    _run(store.save(None, _cp("s10", 5, "later-message"), thread_id="t1", checkpoint_id="cp-later", parent_id=first))
    manager = RecoveryManager(store)

    session = AgentSession(session_id="s10", user_id="u", agent_id="a")
    ok = _run(manager.rollback_and_restore(session, first, prune_descendants=True))
    assert ok is True
    assert session.messages[-1]["content"] == "first-message"
    assert _run(store.get(None, "cp-later")) is None


def test_recovery_manager_rollback_and_restore_missing_returns_false() -> None:
    from app.core.session import AgentSession

    manager = RecoveryManager(InMemoryCheckpointStore())
    session = AgentSession(session_id="s11", user_id="u", agent_id="a")
    assert _run(manager.rollback_and_restore(session, "nope")) is False
