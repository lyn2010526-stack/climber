"""Coverage tests for app.core.execution.engine (TaskExecutionEngine)."""

from __future__ import annotations

from typing import Any

import pytest

from app.core.execution.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, TimeoutManager
from app.core.execution.engine import TaskExecutionEngine
from app.core.execution.event_bus import EventBus
from app.core.execution.hitl import HITLManager
from app.core.execution.task_model import SubTask, Task, TaskStore
from app.core.task_state_machine import TaskState


def _engine(**kwargs: Any) -> TaskExecutionEngine:
    return TaskExecutionEngine(
        task_store=TaskStore(":memory:"),
        event_bus=EventBus(),
        hitl_manager=HITLManager(auto_approve_actions={"execute_subtask"}),
        timeout_manager=TimeoutManager(),
        **kwargs,
    )


async def test_execute_task_without_subtasks_completes() -> None:
    engine = _engine()
    task = Task(goal="simple")
    result = await engine.execute_task(task)
    assert result.status == TaskState.COMPLETED.value
    assert result.current_iteration == 1
    assert "completed_at" in result.metadata
    engine.close()


async def test_execute_task_circuit_breaker_open() -> None:
    cb = CircuitBreaker(CircuitBreakerConfig(max_failures=1))
    cb.record_failure()
    engine = _engine(circuit_breaker=cb)
    task = Task(goal="blocked")
    result = await engine.execute_task(task)
    assert result.status == TaskState.FAILED.value
    assert result.metadata["failure_reason"] == "circuit_breaker_open"
    engine.close()


async def test_execute_task_dag_order() -> None:
    calls: list[str] = []

    def executor(subtask: SubTask, task: Task) -> str:
        calls.append(subtask.id)
        return f"done:{subtask.description}"

    engine = _engine(subtask_executor=executor)
    a = SubTask(description="first")
    b = SubTask(description="second", dependencies=[a.id])
    task = Task(goal="dag", sub_tasks=[a, b])
    result = await engine.execute_task(task)
    assert result.status == TaskState.COMPLETED.value
    assert calls == [a.id, b.id]
    assert a.result == "done:first"
    engine.close()


async def test_execute_task_circular_dependency() -> None:
    a = SubTask(description="a", dependencies=["b"])
    b = SubTask(description="b", dependencies=["a"])
    a.dependencies = [b.id]
    b.dependencies = [a.id]
    engine = _engine()
    task = Task(goal="cycle", sub_tasks=[a, b])
    result = await engine.execute_task(task)
    assert result.status == TaskState.FAILED.value
    assert result.metadata["failure_reason"] == "circular_dependency"
    engine.close()


async def test_execute_task_subtask_exception_fails_task() -> None:
    def executor(subtask: SubTask, task: Task) -> str:
        raise RuntimeError("subtask-boom")

    engine = _engine(subtask_executor=executor)
    st = SubTask(description="work")
    task = Task(goal="boom", sub_tasks=[st])
    result = await engine.execute_task(task)
    assert result.status == TaskState.FAILED.value
    assert st.status == TaskState.FAILED.value
    assert "subtask-boom" in st.error
    engine.close()


async def test_execute_task_hitl_auto_approved() -> None:
    engine = _engine()
    st = SubTask(description="deploy to production")
    task = Task(goal="deploy", sub_tasks=[st])
    result = await engine.execute_task(task)
    assert result.status == TaskState.COMPLETED.value
    engine.close()


async def test_execute_task_hitl_rejected(monkeypatch) -> None:
    engine = _engine()

    async def reject(hitl_request_id: str, task: Task, poll_interval: float = 0.1) -> bool:
        return False

    monkeypatch.setattr(engine, "_wait_for_approval", reject)
    st = SubTask(description="delete database")
    task = Task(goal="danger", sub_tasks=[st])
    result = await engine.execute_task(task)
    assert result.status == TaskState.FAILED.value
    assert st.status == TaskState.FAILED.value
    assert st.error == "HITL rejected"
    engine.close()


async def test_execute_task_task_level_timeout(monkeypatch) -> None:
    engine = _engine()
    monkeypatch.setattr(engine._timeout, "check_timeout", lambda task_id: True)
    st = SubTask(description="work")
    task = Task(goal="timeout", sub_tasks=[st])
    result = await engine.execute_task(task)
    assert result.status == TaskState.FAILED.value
    assert result.metadata["failure_reason"] == "timeout"
    engine.close()


async def test_execute_task_subtask_level_timeout(monkeypatch) -> None:
    engine = _engine()
    monkeypatch.setattr(engine._timeout, "check_timeout", lambda task_id: False)
    monkeypatch.setattr(engine._timeout, "get_remaining_time", lambda task_id: 0.0)
    st = SubTask(description="slow work")
    task = Task(goal="slow", sub_tasks=[st])
    result = await engine.execute_task(task)
    assert result.status == TaskState.FAILED.value
    assert result.metadata["failure_reason"] == "timeout"
    assert st.status == TaskState.FAILED.value
    assert st.error == "timeout"
    engine.close()


async def test_execute_task_generic_exception_sets_failure_reason(monkeypatch) -> None:
    engine = _engine()

    async def boom(task: Task) -> bool:
        raise ValueError("dag-boom")

    monkeypatch.setattr(engine, "_execute_with_dag", boom)
    task = Task(goal="x")
    result = await engine.execute_task(task)
    assert result.status == TaskState.FAILED.value
    assert result.metadata["failure_reason"] == "dag-boom"
    engine.close()


def test_requires_hitl_keywords() -> None:
    engine = _engine()
    assert engine._requires_hitl(SubTask(description="Deploy the service")) is True
    assert engine._requires_hitl(SubTask(description="delete file")) is True
    assert engine._requires_hitl(SubTask(description="destroy instance")) is True
    assert engine._requires_hitl(SubTask(description="read a file")) is False
    engine.close()


def test_get_ready_subtasks() -> None:
    engine = _engine()
    a = SubTask(description="a")
    b = SubTask(description="b", dependencies=[a.id])
    st_map = {a.id: a, b.id: b}
    ready = engine._get_ready_subtasks(st_map, set(), {a.id, b.id})
    assert ready == [a.id]
    ready2 = engine._get_ready_subtasks(st_map, {a.id}, {b.id})
    assert ready2 == [b.id]
    engine.close()


def test_default_subtask_executor() -> None:
    engine = _engine()
    out = engine._default_subtask_executor(SubTask(description="hello"), Task())
    assert out == "Executed: hello"
    engine.close()


async def test_pause_resume_cancel_task() -> None:
    engine = _engine()
    task = Task(goal="lifecycle")
    engine._store.save(task)

    assert await engine.pause_task("missing") is None

    paused = await engine.pause_task(task.id)
    assert paused is not None and paused.status == TaskState.PAUSED.value

    # cancel a task that is not tracked as running
    cancelled_idle = await engine.cancel_task(task.id)
    assert cancelled_idle is not None and cancelled_idle.status == TaskState.CANCELLED.value

    resumed = await engine.resume_task(paused)
    assert resumed.status == TaskState.COMPLETED.value

    class _FakeRunning:
        def __init__(self) -> None:
            self.cancelled = False

        def cancel(self) -> None:
            self.cancelled = True

    fake = _FakeRunning()
    engine._running_tasks[task.id] = fake  # type: ignore[assignment]
    cancelled = await engine.cancel_task(task.id)
    assert cancelled is not None and cancelled.status == TaskState.CANCELLED.value
    assert fake.cancelled is True

    assert await engine.cancel_task("missing") is None
    engine.close()


async def test_execute_task_records_running_task() -> None:
    engine = _engine()
    task = Task(goal="running")
    await engine.execute_task(task)
    # cleanup in finally removes the running entry
    assert task.id not in engine._running_tasks
    engine.close()


async def test_run_subtask_uses_executor() -> None:
    def executor(subtask: SubTask, task: Task) -> int:
        return 42

    engine = _engine(subtask_executor=executor)
    result = await engine._run_subtask(SubTask(description="x"), Task())
    assert result == 42
    engine.close()


async def test_wait_for_approval_timeout_raises(monkeypatch) -> None:
    engine = _engine()
    engine._hitl = HITLManager()
    monkeypatch.setattr(engine._timeout, "get_remaining_time", lambda task_id: 0.0)

    req = engine._hitl.create_request(task_id="t", action_type="execute_subtask", payload={})
    with pytest.raises(TimeoutError):
        await engine._wait_for_approval(req.id, Task())
    engine.close()


async def test_wait_for_approval_missing_request() -> None:
    engine = _engine()
    assert await engine._wait_for_approval("ghost", Task()) is False
    engine.close()


async def test_wait_for_approval_expired_request() -> None:
    engine = _engine()
    engine._hitl = HITLManager(default_ttl_seconds=0)
    req = engine._hitl.create_request(task_id="t", action_type="execute_subtask", payload={})
    assert await engine._wait_for_approval(req.id, Task()) is False
    engine.close()


async def test_wait_for_approval_rejected_request() -> None:
    engine = _engine()
    engine._hitl = HITLManager()
    req = engine._hitl.create_request(task_id="t", action_type="execute_subtask", payload={})
    engine._hitl.reject(req.id, resolved_by="tester")
    assert await engine._wait_for_approval(req.id, Task()) is False
    engine.close()


async def test_wait_for_approval_skips_other_expired(monkeypatch) -> None:
    engine = _engine()
    engine._hitl = HITLManager()
    target = engine._hitl.create_request(task_id="t", action_type="execute_subtask", payload={})
    other = engine._hitl.create_request(task_id="t2", action_type="execute_subtask", payload={})
    monkeypatch.setattr(engine._hitl, "expire_pending", lambda: [other, target])
    assert await engine._wait_for_approval(target.id, Task()) is False
    engine.close()


async def test_wait_for_approval_polls_until_deadline(monkeypatch) -> None:
    engine = _engine()
    engine._hitl = HITLManager()
    pending = engine._hitl.create_request(task_id="t", action_type="execute_subtask", payload={})

    monkeypatch.setattr(engine._hitl, "expire_pending", lambda: [])
    monkeypatch.setattr(engine._timeout, "get_remaining_time", lambda task_id: 0.05)
    with pytest.raises(TimeoutError):
        await engine._wait_for_approval(pending.id, Task(), poll_interval=0.0)
    engine.close()
