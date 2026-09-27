"""Cross-thread checkpoint store and rollback contract tests (research-100 P1c).

Aligned to langgraph persistence: thread-scoped checkpoint namespaces plus
time-travel rollback over the parent chain.
"""

from __future__ import annotations

import pytest

from app.core.checkpoint import CheckpointData, InMemoryCheckpointStore


def _cp(session_id: str, iteration: int, content: str = "") -> CheckpointData:
    return CheckpointData(
        session_id=session_id,
        messages=[{"role": "user", "content": content or f"msg-{iteration}"}],
        iteration=iteration,
        status="running",
    )


@pytest.mark.asyncio
async def test_thread_namespace_isolates_latest() -> None:
    store = InMemoryCheckpointStore()
    await store.save(None, _cp("s1", 1), thread_id="turn-a", checkpoint_id="a1")
    await store.save(None, _cp("s1", 2), thread_id="turn-a", checkpoint_id="a2")
    await store.save(None, _cp("s1", 9), thread_id="turn-b", checkpoint_id="b9")

    latest_a = await store.get_latest(None, "s1", thread_id="turn-a")
    latest_b = await store.get_latest(None, "s1", thread_id="turn-b")
    latest_any = await store.get_latest(None, "s1")

    assert latest_a is not None and latest_a[1] == "a2"
    assert latest_b is not None and latest_b[1] == "b9"
    assert latest_any is not None and latest_any[1] == "b9"


@pytest.mark.asyncio
async def test_get_latest_unknown_thread_returns_none() -> None:
    store = InMemoryCheckpointStore()
    await store.save(None, _cp("s1", 1), thread_id="turn-a", checkpoint_id="a1")
    assert await store.get_latest(None, "s1", thread_id="missing") is None


@pytest.mark.asyncio
async def test_ancestors_walk_parent_chain_newest_first() -> None:
    store = InMemoryCheckpointStore()
    await store.save(None, _cp("s1", 1), checkpoint_id="c1")
    await store.save(None, _cp("s1", 2), checkpoint_id="c2", parent_id="c1")
    await store.save(None, _cp("s1", 3), checkpoint_id="c3", parent_id="c2")

    lineage = await store.get_ancestors("c3")
    assert [cp.iteration for cp in lineage] == [3, 2, 1]


@pytest.mark.asyncio
async def test_ancestors_stops_on_cycle() -> None:
    store = InMemoryCheckpointStore()
    await store.save(None, _cp("s1", 1), checkpoint_id="c1", parent_id="c2")
    await store.save(None, _cp("s1", 2), checkpoint_id="c2", parent_id="c1")

    lineage = await store.get_ancestors("c1")
    assert {cp.iteration for cp in lineage} == {1, 2}
    assert len(lineage) == 2


@pytest.mark.asyncio
async def test_rollback_to_returns_snapshot() -> None:
    store = InMemoryCheckpointStore()
    await store.save(None, _cp("s1", 1, "first"), checkpoint_id="c1")
    await store.save(None, _cp("s1", 2, "second"), checkpoint_id="c2", parent_id="c1")

    snapshot = await store.rollback_to("c1")
    assert snapshot is not None
    assert snapshot.iteration == 1
    # Non-destructive by default: descendant is still present.
    assert await store.get(None, "c2") is not None


@pytest.mark.asyncio
async def test_rollback_to_missing_returns_none() -> None:
    store = InMemoryCheckpointStore()
    assert await store.rollback_to("nope") is None


@pytest.mark.asyncio
async def test_rollback_prune_removes_descendants_only() -> None:
    store = InMemoryCheckpointStore()
    await store.save(None, _cp("s1", 1), thread_id="t", checkpoint_id="c1")
    await store.save(None, _cp("s1", 2), thread_id="t", checkpoint_id="c2", parent_id="c1")
    await store.save(None, _cp("s1", 3), thread_id="t", checkpoint_id="c3", parent_id="c2")
    await store.save(None, _cp("s1", 5), thread_id="t", checkpoint_id="side", parent_id="c1")

    snapshot = await store.rollback_to("c2", prune_descendants=True)
    assert snapshot is not None and snapshot.iteration == 2
    # c3 descends from c2 -> removed; c1 (ancestor) and side (sibling branch) kept.
    assert await store.get(None, "c3") is None
    assert await store.get(None, "c1") is not None
    assert await store.get(None, "side") is not None
    # Thread index no longer references the pruned checkpoint.
    latest = await store.get_latest(None, "s1", thread_id="t")
    assert latest is not None and latest[1] == "side"


@pytest.mark.asyncio
async def test_delete_for_session_clears_thread_index() -> None:
    store = InMemoryCheckpointStore()
    await store.save(None, _cp("s1", 1), thread_id="t", checkpoint_id="c1")
    removed = await store.delete_for_session(None, "s1")
    assert removed == 1
    assert await store.get_latest(None, "s1", thread_id="t") is None


@pytest.mark.asyncio
async def test_engine_save_checkpoint_threads_and_links_parent() -> None:
    from types import SimpleNamespace

    from app.core.agent_engine import AgentEngine

    store = InMemoryCheckpointStore()
    engine = object.__new__(AgentEngine)
    engine._checkpoints = store

    session = SimpleNamespace(session_id="s1", current_turn_id="turn-7")
    first = await engine._save_checkpoint(session, _cp("s1", 1), "s1-1")
    second = await engine._save_checkpoint(session, _cp("s1", 2), "s1-2")

    # Both checkpoints filed under the session's current turn thread.
    latest = await store.get_latest(None, "s1", thread_id="turn-7")
    assert latest is not None and latest[1] == second
    # The second checkpoint chains back to the first.
    lineage = await store.get_ancestors(second)
    assert [cp.iteration for cp in lineage] == [2, 1]
    assert first != second

