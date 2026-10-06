"""Coverage tests for app.core.engine.subagent."""

from __future__ import annotations

import asyncio
import time

import pytest

from app.core.engine.subagent import (
    ConcurrencyLimitExceeded,
    DepthLimitExceeded,
    SubagentManager,
    SubagentRecord,
    SubagentSpec,
    SubagentState,
    SubagentUsage,
)


async def _ok_runner(_spec: SubagentSpec) -> tuple[str, SubagentUsage]:
    return "ok", SubagentUsage(tokens_in=3, tokens_out=4, cost_usd=0.01, tool_calls=2)


def test_usage_to_dict_rounds() -> None:
    usage = SubagentUsage(tokens_in=1, tokens_out=2, cost_usd=0.1234567, duration_ms=1.2345)
    data = usage.to_dict()
    assert data["tokens_in"] == 1
    assert data["cost_usd"] == 0.123457
    assert data["duration_ms"] == 1.23


def test_record_properties() -> None:
    rec = SubagentRecord(spec=SubagentSpec())
    assert rec.duration_ms == 0.0
    assert rec.is_active is True
    rec.started_at = 10.0
    rec.completed_at = 10.5
    assert rec.duration_ms == pytest.approx(500.0)


def test_record_duration_running_uses_now() -> None:
    rec = SubagentRecord(spec=SubagentSpec())
    rec.started_at = time.monotonic()
    assert rec.duration_ms >= 0.0


def test_record_is_active_only_pending_running() -> None:
    for state, expected in [
        (SubagentState.PENDING, True),
        (SubagentState.RUNNING, True),
        (SubagentState.COMPLETED, False),
        (SubagentState.FAILED, False),
        (SubagentState.ORPHANED, False),
    ]:
        assert SubagentRecord(spec=SubagentSpec(), state=state).is_active is expected


def test_record_to_dict_truncates_result() -> None:
    rec = SubagentRecord(spec=SubagentSpec(depth=2, parent_id="p"), result="x" * 500)
    data = rec.to_dict()
    assert len(data["result"]) == 200
    assert data["depth"] == 2
    assert data["parent_id"] == "p"
    assert data["child_ids"] == []


async def test_spawn_success_records_usage() -> None:
    manager = SubagentManager(concurrency_limit=2)
    record = await manager.spawn(SubagentSpec(description="t"), _ok_runner)
    assert record.state is SubagentState.COMPLETED
    assert record.result == "ok"
    assert record.usage.tokens_in == 3
    assert record.started_at is not None
    assert record.completed_at is not None
    assert manager.active_count == 0
    assert manager.total_count == 1


async def test_spawn_registers_child_of_known_parent() -> None:
    manager = SubagentManager(concurrency_limit=2)
    parent = await manager.spawn(SubagentSpec(description="parent"), _ok_runner)
    assert parent.state is SubagentState.COMPLETED
    child = await manager.spawn(
        SubagentSpec(description="child", parent_id=parent.spec.task_id), _ok_runner
    )
    assert child.state is SubagentState.COMPLETED
    assert manager.get_children(parent.spec.task_id) == [child]


async def test_spawn_child_with_unknown_parent_is_ignored() -> None:
    manager = SubagentManager(concurrency_limit=1)
    child = await manager.spawn(SubagentSpec(parent_id="ghost"), _ok_runner)
    assert child.state is SubagentState.COMPLETED
    assert manager.get_children("ghost") == []


def test_cancel_active_record_without_event() -> None:
    manager = SubagentManager()
    record = SubagentRecord(spec=SubagentSpec(task_id="r"), state=SubagentState.RUNNING)
    manager._records["r"] = record
    assert manager.cancel("r") is True


async def test_cleanup_orphans_skips_non_running() -> None:
    manager = SubagentManager(orphan_timeout=1.0)
    completed = SubagentRecord(
        spec=SubagentSpec(task_id="done", parent_id="dead"), state=SubagentState.COMPLETED
    )
    manager._records = {"done": completed}
    assert await manager.cleanup_orphans() == []
    assert completed.state is SubagentState.COMPLETED


async def test_spawn_depth_limit_exceeded() -> None:
    manager = SubagentManager(depth_limit=3)
    record = await manager.spawn(SubagentSpec(depth=3), _ok_runner)
    assert record.state is SubagentState.FAILED
    assert record.error == "Depth limit (3) exceeded"
    assert manager.get_record(record.spec.task_id) is record


async def test_spawn_timeout() -> None:
    manager = SubagentManager(concurrency_limit=1)

    async def slow(_spec: SubagentSpec) -> tuple[str, SubagentUsage]:
        await asyncio.sleep(0.1)
        return "late", SubagentUsage()

    record = await manager.spawn(SubagentSpec(timeout_seconds=0.01), slow)
    assert record.state is SubagentState.TIMED_OUT
    assert "Timeout after" in (record.error or "")


async def test_spawn_exception_marks_failed() -> None:
    manager = SubagentManager(concurrency_limit=1)

    async def boom(_spec: SubagentSpec) -> tuple[str, SubagentUsage]:
        raise ValueError("nope")

    record = await manager.spawn(SubagentSpec(), boom)
    assert record.state is SubagentState.FAILED
    assert record.error == "nope"


async def test_spawn_cancel_marks_cancelled() -> None:
    manager = SubagentManager(concurrency_limit=1)
    started = asyncio.Event()
    blocker = asyncio.Event()

    async def waiter(_spec: SubagentSpec) -> tuple[str, SubagentUsage]:
        started.set()
        await blocker.wait()
        return "never", SubagentUsage()

    spec = SubagentSpec()
    task = asyncio.create_task(manager.spawn(spec, waiter))
    await started.wait()
    assert manager.cancel(spec.task_id) is True
    record = await task
    assert record.state is SubagentState.CANCELLED
    assert record.error == "Cancelled by parent"


async def test_spawn_concurrency_acquisition_timeout() -> None:
    manager = SubagentManager(concurrency_limit=1)

    class _BoomSemaphore:
        def locked(self) -> bool:
            return True

        async def acquire(self) -> bool:
            raise TimeoutError

        def release(self) -> None:
            pass

    manager._semaphore = _BoomSemaphore()  # type: ignore[assignment]
    record = await manager.spawn(SubagentSpec(), _ok_runner)
    assert record.state is SubagentState.FAILED
    assert record.error == "Concurrency acquisition timeout"


async def test_run_with_cancel_without_event_uses_runner() -> None:
    manager = SubagentManager(concurrency_limit=1)
    spec = SubagentSpec()
    result, usage = await manager._run_with_cancel(spec, _ok_runner)
    assert result == "ok"
    assert usage.tokens_out == 4


def test_get_record_and_children() -> None:
    manager = SubagentManager()
    parent = SubagentRecord(spec=SubagentSpec(task_id="p"))
    child = SubagentRecord(spec=SubagentSpec(task_id="c", parent_id="p"))
    manager._records = {"p": parent, "c": child}
    parent.child_ids.append("c")
    assert manager.get_record("p") is parent
    assert manager.get_record("missing") is None
    assert manager.get_children("p") == [child]
    assert manager.get_children("unknown") == []


def test_get_active_runs() -> None:
    manager = SubagentManager()
    running = SubagentRecord(spec=SubagentSpec(task_id="r"), state=SubagentState.RUNNING)
    done = SubagentRecord(spec=SubagentSpec(task_id="d"), state=SubagentState.COMPLETED)
    manager._records = {"r": running, "d": done}
    assert manager.get_active_runs() == [running]
    assert manager.active_count == 1


def test_cancel_unknown_or_inactive_returns_false() -> None:
    manager = SubagentManager()
    assert manager.cancel("missing") is False
    done = SubagentRecord(spec=SubagentSpec(task_id="d"), state=SubagentState.COMPLETED)
    manager._records["d"] = done
    assert manager.cancel("d") is False


def test_cancel_cascades_to_children() -> None:
    manager = SubagentManager(enable_cascade_cancel=True)
    parent = SubagentRecord(spec=SubagentSpec(task_id="p"), state=SubagentState.RUNNING)
    child = SubagentRecord(
        spec=SubagentSpec(task_id="c", parent_id="p"), state=SubagentState.RUNNING
    )
    manager._records = {"p": parent, "c": child}
    parent.child_ids.append("c")
    manager._cancel_events = {"p": asyncio.Event(), "c": asyncio.Event()}
    assert manager.cancel("p") is True
    assert manager._cancel_events["p"].is_set()
    assert manager._cancel_events["c"].is_set()


def test_cancel_without_cascade_leaves_children() -> None:
    manager = SubagentManager(enable_cascade_cancel=False)
    parent = SubagentRecord(spec=SubagentSpec(task_id="p"), state=SubagentState.RUNNING)
    child = SubagentRecord(
        spec=SubagentSpec(task_id="c", parent_id="p"), state=SubagentState.RUNNING
    )
    manager._records = {"p": parent, "c": child}
    parent.child_ids.append("c")
    manager._cancel_events = {"p": asyncio.Event(), "c": asyncio.Event()}
    assert manager.cancel("p") is True
    assert manager._cancel_events["p"].is_set()
    assert not manager._cancel_events["c"].is_set()


async def test_cleanup_orphans() -> None:
    manager = SubagentManager(orphan_timeout=10.0)
    now = time.monotonic()
    root = SubagentRecord(spec=SubagentSpec(task_id="root"), state=SubagentState.RUNNING)
    child_of_active = SubagentRecord(
        spec=SubagentSpec(task_id="c1", parent_id="root"),
        state=SubagentState.RUNNING,
        started_at=now - 100,
    )
    orphan = SubagentRecord(
        spec=SubagentSpec(task_id="o1", parent_id="dead"),
        state=SubagentState.RUNNING,
        started_at=now - 100,
    )
    fresh = SubagentRecord(
        spec=SubagentSpec(task_id="o2", parent_id="dead"),
        state=SubagentState.RUNNING,
        started_at=now - 1,
    )
    manager._records = {
        "root": root,
        "c1": child_of_active,
        "o1": orphan,
        "o2": fresh,
    }
    orphaned = await manager.cleanup_orphans()
    assert orphaned == ["o1"]
    assert orphan.state is SubagentState.ORPHANED
    assert orphan.completed_at is not None
    assert "Orphaned (parent dead inactive" in (orphan.error or "")
    assert fresh.state is SubagentState.RUNNING
    assert child_of_active.state is SubagentState.RUNNING


def test_get_stats_aggregates() -> None:
    manager = SubagentManager(depth_limit=4, concurrency_limit=2)
    completed = SubagentRecord(
        spec=SubagentSpec(task_id="a"),
        state=SubagentState.COMPLETED,
        usage=SubagentUsage(tokens_in=10, tokens_out=5, cost_usd=0.5),
        started_at=10.0,
        completed_at=11.0,
    )
    running = SubagentRecord(spec=SubagentSpec(task_id="b"), state=SubagentState.RUNNING)
    manager._records = {"a": completed, "b": running}
    stats = manager.get_stats()
    assert stats["total"] == 2
    assert stats["active"] == 1
    assert stats["states"] == {"completed": 1, "running": 1}
    assert stats["total_tokens"] == 15
    assert stats["total_cost_usd"] == 0.5
    assert stats["avg_duration_ms"] == 1000.0
    assert stats["depth_limit"] == 4
    assert stats["concurrency_limit"] == 2


def test_get_stats_empty_average() -> None:
    stats = SubagentManager().get_stats()
    assert stats["avg_duration_ms"] == 0.0


def test_exception_classes_exist() -> None:
    assert issubclass(DepthLimitExceeded, Exception)
    assert issubclass(ConcurrencyLimitExceeded, Exception)
