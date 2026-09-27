"""RecoveryManager replay filtering tests.

`recover_session` returned every recorded `tool_results` entry, including the
ones produced by `write_file` and `run_command`. A caller that fed those back to
the model would be asserting that a write happened, when the checkpoint can
only say that it happened once before a crash.

These tests pin the split: read results survive recovery, write and command
results are withheld and reported separately, and a checkpoint with no tool
results behaves the same as before.
"""

from __future__ import annotations

import pytest

from app.core.checkpoint import CheckpointData, InMemoryCheckpointStore
from app.core.recovery import RecoveryManager


def make_checkpoint(results: list[dict]) -> CheckpointData:
    return CheckpointData(
        session_id="s1",
        messages=[{"role": "user", "content": "hi"}],
        iteration=3,
        status="interrupted",
        tool_results=results,
    )


@pytest.mark.asyncio
async def test_read_results_are_replayed() -> None:
    store = InMemoryCheckpointStore()
    await store.save(None, make_checkpoint([{"tool": "read_file", "result": "ok"}]))
    manager = RecoveryManager(store)

    recovered = await manager.recover_session("s1")

    assert recovered is not None
    assert [r["tool"] for r in recovered["tool_results"]] == ["read_file"]


@pytest.mark.asyncio
async def test_write_results_are_withheld() -> None:
    store = InMemoryCheckpointStore()
    await store.save(
        None,
        make_checkpoint(
            [
                {"tool": "read_file", "result": "ok"},
                {"tool": "write_file", "result": "wrote"},
            ]
        ),
    )
    manager = RecoveryManager(store)

    recovered = await manager.recover_session("s1")

    assert [r["tool"] for r in recovered["tool_results"]] == ["read_file"]
    assert [r["tool"] for r in recovered["withheld_tool_results"]] == ["write_file"]


@pytest.mark.asyncio
async def test_command_results_are_withheld() -> None:
    store = InMemoryCheckpointStore()
    await store.save(None, make_checkpoint([{"tool": "run_command", "result": "done"}]))
    manager = RecoveryManager(store)

    recovered = await manager.recover_session("s1")

    assert recovered["tool_results"] == []
    assert len(recovered["withheld_tool_results"]) == 1


@pytest.mark.asyncio
async def test_identical_entries_are_classified_independently() -> None:
    """Two identical dicts are two side effects, not one.

    Deduplicating by value would drop a second write that really happened.
    """
    store = InMemoryCheckpointStore()
    await store.save(
        None,
        make_checkpoint(
            [
                {"tool": "write_file", "result": "same"},
                {"tool": "write_file", "result": "same"},
            ]
        ),
    )
    manager = RecoveryManager(store)

    recovered = await manager.recover_session("s1")

    assert len(recovered["withheld_tool_results"]) == 2


@pytest.mark.asyncio
async def test_no_tool_results_yields_empty_lists() -> None:
    store = InMemoryCheckpointStore()
    await store.save(None, make_checkpoint([]))
    manager = RecoveryManager(store)

    recovered = await manager.recover_session("s1")

    assert recovered["tool_results"] == []
    assert recovered["withheld_tool_results"] == []


@pytest.mark.asyncio
async def test_unknown_session_still_returns_none() -> None:
    manager = RecoveryManager(InMemoryCheckpointStore())
    assert await manager.recover_session("nope") is None


@pytest.mark.asyncio
async def test_existing_recovery_fields_are_untouched() -> None:
    """The split must not drop fields other code already depends on."""
    store = InMemoryCheckpointStore()
    await store.save(None, make_checkpoint([{"tool": "read_file", "result": "ok"}]))
    manager = RecoveryManager(store)

    recovered = await manager.recover_session("s1")

    for field in (
        "session_id",
        "messages",
        "iteration",
        "status",
        "channel_values",
        "channel_versions",
        "versions_seen",
        "pending_writes",
        "interrupted",
        "checkpoint_id",
        "checkpoint",
    ):
        assert field in recovered, f"{field} disappeared from the recovery payload"

