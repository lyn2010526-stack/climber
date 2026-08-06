"""Tests for AGI P3 Execution Layer.

Covers: task model CRUD, event bus, HITL lifecycle,
circuit breaker, timeout manager, and execution engine.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from app.core.execution.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
    TimeoutManager,
)
from app.core.execution.engine import TaskExecutionEngine
from app.core.execution.event_bus import EventBus, TaskEvent
from app.core.execution.hitl import (
    HITLManager,
    HITLStatusApproved,
    HITLStatusExpired,
    HITLStatusPending,
    HITLStatusRejected,
)
from app.core.execution.task_model import SubTask, Task, TaskStore
from app.core.task_state_machine import TaskState

# ---------------------------------------------------------------------------
# Task Model Tests
# ---------------------------------------------------------------------------


class TestSubTask:
    def test_create_default(self):
        st = SubTask(description="test step")
        assert st.description == "test step"
        assert st.status == TaskState.PENDING.value
        assert st.dependencies == []
        assert st.assigned_agent == ""
        assert st.result == ""
        assert st.error == ""

    def test_to_dict(self):
        st = SubTask(id="st-1", description="do thing", dependencies=["st-0"])
        d = st.to_dict()
        assert d["id"] == "st-1"
        assert d["description"] == "do thing"
        assert d["dependencies"] == ["st-0"]

    def test_from_dict(self):
        data = {
            "id": "st-2",
            "description": "reconstruct",
            "status": "running",
            "dependencies": ["st-1"],
            "assigned_agent": "agent-a",
            "result": "",
            "error": "",
            "started_at": "",
            "completed_at": "",
            "metadata": {},
        }
        st = SubTask.from_dict(data)
        assert st.id == "st-2"
        assert st.status == "running"
        assert st.dependencies == ["st-1"]


class TestTask:
    def test_create_default(self):
        task = Task(goal="build feature")
        assert task.goal == "build feature"
        assert task.status == TaskState.PENDING.value
        assert task.sub_tasks == []
        assert task.max_iterations == 100
        assert task.current_iteration == 0
        assert task.timeout_seconds == 3600
        assert task.parent_id == ""

    def test_to_dict(self):
        task = Task(id="t-1", goal="test", sub_tasks=[SubTask(id="st-1", description="step")])
        d = task.to_dict()
        assert d["id"] == "t-1"
        assert d["goal"] == "test"
        assert len(d["sub_tasks"]) == 1
        assert d["sub_tasks"][0]["id"] == "st-1"

    def test_from_dict(self):
        data = {
            "id": "t-2",
            "goal": "reconstruct",
            "status": "running",
            "sub_tasks": [{"id": "st-1", "description": "s", "status": "completed",
                          "dependencies": [], "assigned_agent": "", "result": "ok",
                          "error": "", "started_at": "", "completed_at": "", "metadata": {}}],
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:01:00",
            "max_iterations": 50,
            "current_iteration": 1,
            "timeout_seconds": 120,
            "parent_id": "t-0",
            "metadata": {"key": "val"},
        }
        task = Task.from_dict(data)
        assert task.id == "t-2"
        assert task.parent_id == "t-0"
        assert len(task.sub_tasks) == 1
        assert task.sub_tasks[0].result == "ok"


class TestTaskStore:
    def test_save_and_load(self):
        store = TaskStore()
        task = Task(id="t-1", goal="test goal")
        store.save(task)
        loaded = store.load("t-1")
        assert loaded is not None
        assert loaded.goal == "test goal"
        store.close()

    def test_load_not_found(self):
        store = TaskStore()
        assert store.load("nonexistent") is None
        store.close()

    def test_update(self):
        store = TaskStore()
        task = Task(id="t-1", goal="original")
        store.save(task)
        task.goal = "updated"
        store.update(task)
        loaded = store.load("t-1")
        assert loaded is not None
        assert loaded.goal == "updated"
        store.close()

    def test_delete(self):
        store = TaskStore()
        task = Task(id="t-1", goal="to delete")
        store.save(task)
        assert store.delete("t-1") is True
        assert store.load("t-1") is None
        assert store.delete("t-1") is False
        store.close()

    def test_list_all(self):
        store = TaskStore()
        store.save(Task(id="t-1", goal="a"))
        store.save(Task(id="t-2", goal="b"))
        tasks = store.list_all()
        assert len(tasks) == 2
        store.close()

    def test_get_children(self):
        store = TaskStore()
        store.save(Task(id="parent", goal="parent"))
        store.save(Task(id="child-1", goal="c1", parent_id="parent"))
        store.save(Task(id="child-2", goal="c2", parent_id="parent"))
        store.save(Task(id="other", goal="standalone"))
        children = store.get_children("parent")
        assert len(children) == 2
        store.close()

    def test_persistence_across_instances(self, tmp_path):
        db_file = str(tmp_path / "tasks.db")
        store1 = TaskStore(db_path=db_file)
        store1.save(Task(id="persist-1", goal="persistent"))
        store1.close()
        store2 = TaskStore(db_path=db_file)
        loaded = store2.load("persist-1")
        assert loaded is not None
        assert loaded.goal == "persistent"
        store2.close()


# ---------------------------------------------------------------------------
# Event Bus Tests
# ---------------------------------------------------------------------------


class TestTaskEvent:
    def test_create(self):
        event = TaskEvent(event_type="created", task_id="t-1")
        assert event.event_type == "created"
        assert event.task_id == "t-1"
        assert event.event_id != ""
        assert event.data == {}

    def test_to_dict(self):
        event = TaskEvent(event_type="started", task_id="t-1", data={"key": "val"})
        d = event.to_dict()
        assert d["event_type"] == "started"
        assert d["task_id"] == "t-1"
        assert d["data"] == {"key": "val"}


class TestEventBus:
    @pytest.mark.asyncio
    async def test_publish_and_receive(self):
        bus = EventBus()
        received = []

        async def handler(event: TaskEvent):
            received.append(event)

        bus.subscribe("created", handler)
        event = TaskEvent(event_type="created", task_id="t-1")
        await bus.publish(event)
        await asyncio.sleep(0.05)
        assert len(received) == 1
        assert received[0].task_id == "t-1"
        bus.close()

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        bus = EventBus()
        received = []

        async def handler(event: TaskEvent):
            received.append(event)

        bus.subscribe("created", handler)
        bus.unsubscribe("created", handler)
        await bus.publish(TaskEvent(event_type="created", task_id="t-1"))
        await asyncio.sleep(0.05)
        assert len(received) == 0
        bus.close()

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        bus = EventBus()
        count = [0]

        async def handler1(event: TaskEvent):
            count[0] += 1

        async def handler2(event: TaskEvent):
            count[0] += 1

        bus.subscribe("completed", handler1)
        bus.subscribe("completed", handler2)
        await bus.publish(TaskEvent(event_type="completed", task_id="t-1"))
        await asyncio.sleep(0.05)
        assert count[0] == 2
        bus.close()

    def test_history_persistence(self):
        bus = EventBus()
        asyncio.run(bus.publish(TaskEvent(event_type="created", task_id="t-1")))
        asyncio.run(bus.publish(TaskEvent(event_type="started", task_id="t-1")))
        asyncio.run(bus.publish(TaskEvent(event_type="completed", task_id="t-1")))
        history = bus.get_history(task_id="t-1")
        assert len(history) == 3
        bus.close()

    def test_history_filter_by_type(self):
        bus = EventBus()
        asyncio.run(bus.publish(TaskEvent(event_type="created", task_id="t-1")))
        asyncio.run(bus.publish(TaskEvent(event_type="failed", task_id="t-2")))
        asyncio.run(bus.publish(TaskEvent(event_type="created", task_id="t-3")))
        history = bus.get_history(event_type="created")
        assert len(history) == 2
        bus.close()

    def test_clear_history(self):
        bus = EventBus()
        asyncio.run(bus.publish(TaskEvent(event_type="created", task_id="t-1")))
        bus.clear_history()
        assert bus.get_history() == []
        bus.close()


# ---------------------------------------------------------------------------
# HITL Tests
# ---------------------------------------------------------------------------


class TestHITLManager:
    def test_create_request(self):
        manager = HITLManager()
        req = manager.create_request(task_id="t-1", action_type="deploy", payload={"env": "prod"})
        assert req.task_id == "t-1"
        assert req.action_type == "deploy"
        assert req.payload == {"env": "prod"}
        assert req.status == HITLStatusPending
        manager.close()

    def test_approve(self):
        manager = HITLManager()
        req = manager.create_request(task_id="t-1", action_type="deploy")
        result = manager.approve(req.id)
        assert result is not None
        assert result.status == HITLStatusApproved
        assert result.resolved_by == "human"
        manager.close()

    def test_reject(self):
        manager = HITLManager()
        req = manager.create_request(task_id="t-1", action_type="deploy")
        result = manager.reject(req.id)
        assert result is not None
        assert result.status == HITLStatusRejected
        manager.close()

    def test_expire(self):
        manager = HITLManager()
        req = manager.create_request(task_id="t-1", action_type="deploy")
        result = manager.expire(req.id)
        assert result is not None
        assert result.status == HITLStatusExpired
        manager.close()

    def test_approve_already_resolved_returns_none(self):
        manager = HITLManager()
        req = manager.create_request(task_id="t-1", action_type="deploy")
        manager.approve(req.id)
        result = manager.approve(req.id)
        assert result is None
        manager.close()

    def test_get_pending(self):
        manager = HITLManager()
        manager.create_request(task_id="t-1", action_type="deploy")
        manager.create_request(task_id="t-2", action_type="delete")
        pending = manager.get_pending()
        assert len(pending) == 2
        manager.close()

    def test_get_pending_filtered_by_task(self):
        manager = HITLManager()
        manager.create_request(task_id="t-1", action_type="deploy")
        manager.create_request(task_id="t-2", action_type="delete")
        pending = manager.get_pending(task_id="t-1")
        assert len(pending) == 1
        assert pending[0].task_id == "t-1"
        manager.close()

    def test_expire_pending(self):
        manager = HITLManager()
        req = manager.create_request(task_id="t-1", action_type="deploy", ttl_seconds=0)
        import time
        time.sleep(0.01)
        expired = manager.expire_pending()
        assert len(expired) == 1
        assert expired[0].id == req.id
        pending = manager.get_pending()
        assert len(pending) == 0
        manager.close()

    def test_auto_approve_actions(self):
        manager = HITLManager(auto_approve_actions={"read", "list"})
        req = manager.create_request(task_id="t-1", action_type="read")
        assert req.status == HITLStatusApproved
        assert req.resolved_by == "auto"
        manager.close()

    def test_get_requests_for_task(self):
        manager = HITLManager()
        manager.create_request(task_id="t-1", action_type="deploy")
        manager.create_request(task_id="t-1", action_type="rollback")
        manager.create_request(task_id="t-2", action_type="delete")
        requests = manager.get_requests_for_task("t-1")
        assert len(requests) == 2
        manager.close()

    def test_get_request_not_found(self):
        manager = HITLManager()
        assert manager.get_request("nonexistent") is None
        manager.close()


# ---------------------------------------------------------------------------
# Circuit Breaker Tests
# ---------------------------------------------------------------------------


class TestCircuitBreaker:
    def test_initial_state(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.is_open is False
        assert cb.allow_request() is True

    def test_trip_after_max_failures(self):
        cb = CircuitBreaker(config=CircuitBreakerConfig(max_failures=3))
        assert cb.record_failure() is False
        assert cb.record_failure() is False
        assert cb.record_failure() is True
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.allow_request() is False

    def test_half_open_after_recovery_timeout(self):
        cb = CircuitBreaker(config=CircuitBreakerConfig(max_failures=1, recovery_timeout=0.1))
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        time.sleep(0.15)
        assert cb.state == CircuitBreakerState.HALF_OPEN
        assert cb.allow_request() is True

    def test_close_after_success_in_half_open(self):
        cb = CircuitBreaker(config=CircuitBreakerConfig(max_failures=1, recovery_timeout=0.1))
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitBreakerState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED

    def test_reopen_on_failure_in_half_open(self):
        cb = CircuitBreaker(config=CircuitBreakerConfig(max_failures=1, recovery_timeout=0.1))
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitBreakerState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

    def test_reset(self):
        cb = CircuitBreaker(config=CircuitBreakerConfig(max_failures=1))
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        cb.reset()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    def test_get_record(self):
        cb = CircuitBreaker(name="test-breaker")
        cb.record_failure()
        record = cb.get_record()
        assert record.state == CircuitBreakerState.CLOSED.value
        assert record.failure_count == 1

    def test_failure_window(self):
        cb = CircuitBreaker(config=CircuitBreakerConfig(max_failures=2, failure_window=0.2))
        cb.record_failure()
        time.sleep(0.25)
        cb.record_failure()
        assert cb.state == CircuitBreakerState.CLOSED


class TestTimeoutManager:
    def test_start_and_check(self):
        tm = TimeoutManager()
        tm.start_task("t-1", timeout_seconds=60)
        assert tm.check_timeout("t-1") is False
        tm.close()

    def test_timeout_exceeded(self):
        tm = TimeoutManager()
        tm.start_task("t-1", timeout_seconds=0)
        time.sleep(0.01)
        assert tm.check_timeout("t-1") is True
        tm.close()

    def test_get_timed_out_tasks(self):
        tm = TimeoutManager()
        tm.start_task("t-1", timeout_seconds=0)
        tm.start_task("t-2", timeout_seconds=60)
        time.sleep(0.01)
        timed_out = tm.get_timed_out_tasks()
        assert "t-1" in timed_out
        assert "t-2" not in timed_out
        tm.close()

    def test_complete_task(self):
        tm = TimeoutManager()
        tm.start_task("t-1", timeout_seconds=60)
        tm.complete_task("t-1")
        assert tm.check_timeout("t-1") is False
        tm.close()

    def test_remaining_time(self):
        tm = TimeoutManager()
        tm.start_task("t-1", timeout_seconds=60)
        remaining = tm.get_remaining_time("t-1")
        assert remaining > 0
        assert remaining <= 60
        tm.close()


# ---------------------------------------------------------------------------
# Execution Engine Tests
# ---------------------------------------------------------------------------


class TestTaskExecutionEngine:
    @pytest.mark.asyncio
    async def test_execute_simple_task(self):
        store = TaskStore()
        bus = EventBus()
        hitl = HITLManager()
        cb = CircuitBreaker()
        tm = TimeoutManager()
        engine = TaskExecutionEngine(
            task_store=store,
            event_bus=bus,
            hitl_manager=hitl,
            circuit_breaker=cb,
            timeout_manager=tm,
        )
        task = Task(id="t-1", goal="simple task")
        result = await engine.execute_task(task)
        assert result.status == TaskState.COMPLETED.value
        events = bus.get_history(task_id="t-1")
        event_types = [e.event_type for e in events]
        assert EventBus.EVENT_STARTED in event_types
        assert EventBus.EVENT_COMPLETED in event_types
        engine.close()

    @pytest.mark.asyncio
    async def test_execute_with_dependencies(self):
        store = TaskStore()
        bus = EventBus()
        hitl = HITLManager()
        cb = CircuitBreaker()
        tm = TimeoutManager()
        engine = TaskExecutionEngine(
            task_store=store,
            event_bus=bus,
            hitl_manager=hitl,
            circuit_breaker=cb,
            timeout_manager=tm,
        )
        task = Task(
            id="t-1",
            goal="with deps",
            sub_tasks=[
                SubTask(id="st-1", description="step one"),
                SubTask(id="st-2", description="step two", dependencies=["st-1"]),
                SubTask(id="st-3", description="step three", dependencies=["st-2"]),
            ],
        )
        result = await engine.execute_task(task)
        assert result.status == TaskState.COMPLETED.value
        st_map = {st.id: st for st in result.sub_tasks}
        assert st_map["st-1"].status == TaskState.COMPLETED.value
        assert st_map["st-2"].status == TaskState.COMPLETED.value
        assert st_map["st-3"].status == TaskState.COMPLETED.value
        engine.close()

    @pytest.mark.asyncio
    async def test_execute_with_parallel_dependencies(self):
        store = TaskStore()
        bus = EventBus()
        hitl = HITLManager()
        cb = CircuitBreaker()
        tm = TimeoutManager()
        engine = TaskExecutionEngine(
            task_store=store,
            event_bus=bus,
            hitl_manager=hitl,
            circuit_breaker=cb,
            timeout_manager=tm,
        )
        task = Task(
            id="t-1",
            goal="parallel",
            sub_tasks=[
                SubTask(id="st-1", description="root"),
                SubTask(id="st-2", description="branch a", dependencies=["st-1"]),
                SubTask(id="st-3", description="branch b", dependencies=["st-1"]),
                SubTask(id="st-4", description="final", dependencies=["st-2", "st-3"]),
            ],
        )
        result = await engine.execute_task(task)
        assert result.status == TaskState.COMPLETED.value
        engine.close()

    @pytest.mark.asyncio
    async def test_timeout_enforcement(self):
        store = TaskStore()
        bus = EventBus()
        hitl = HITLManager()
        cb = CircuitBreaker()
        tm = TimeoutManager()

        def slow_executor(subtask: SubTask, task: Task) -> str:
            time.sleep(1)
            return "done"

        engine = TaskExecutionEngine(
            task_store=store,
            event_bus=bus,
            hitl_manager=hitl,
            circuit_breaker=cb,
            timeout_manager=tm,
            subtask_executor=slow_executor,
        )
        task = Task(
            id="t-1",
            goal="timeout test",
            timeout_seconds=0,
            sub_tasks=[SubTask(id="st-1", description="slow step")],
        )
        result = await engine.execute_task(task)
        assert result.status == TaskState.FAILED.value
        engine.close()

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_execution(self):
        store = TaskStore()
        bus = EventBus()
        hitl = HITLManager()
        cb = CircuitBreaker(config=CircuitBreakerConfig(max_failures=1))
        cb.record_failure()
        assert cb.is_open
        tm = TimeoutManager()
        engine = TaskExecutionEngine(
            task_store=store,
            event_bus=bus,
            hitl_manager=hitl,
            circuit_breaker=cb,
            timeout_manager=tm,
        )
        task = Task(id="t-1", goal="blocked")
        result = await engine.execute_task(task)
        assert result.status == TaskState.FAILED.value
        assert result.metadata.get("failure_reason") == "circuit_breaker_open"
        engine.close()

    @pytest.mark.asyncio
    async def test_cancel_task(self):
        store = TaskStore()
        bus = EventBus()
        hitl = HITLManager()
        cb = CircuitBreaker()
        tm = TimeoutManager()
        engine = TaskExecutionEngine(
            task_store=store,
            event_bus=bus,
            hitl_manager=hitl,
            circuit_breaker=cb,
            timeout_manager=tm,
        )
        task = Task(id="t-1", goal="to cancel")
        store.save(task)
        result = await engine.cancel_task("t-1")
        assert result is not None
        assert result.status == TaskState.CANCELLED.value
        engine.close()

    @pytest.mark.asyncio
    async def test_pause_task(self):
        store = TaskStore()
        bus = EventBus()
        hitl = HITLManager()
        cb = CircuitBreaker()
        tm = TimeoutManager()
        engine = TaskExecutionEngine(
            task_store=store,
            event_bus=bus,
            hitl_manager=hitl,
            circuit_breaker=cb,
            timeout_manager=tm,
        )
        task = Task(id="t-1", goal="to pause")
        store.save(task)
        result = await engine.pause_task("t-1")
        assert result is not None
        assert result.status == TaskState.PAUSED.value
        engine.close()

    @pytest.mark.asyncio
    async def test_hitl_rejection_fails_subtask(self):
        store = TaskStore()
        bus = EventBus()
        hitl = HITLManager(auto_approve_actions=set())
        cb = CircuitBreaker()
        tm = TimeoutManager()
        engine = TaskExecutionEngine(
            task_store=store,
            event_bus=bus,
            hitl_manager=hitl,
            circuit_breaker=cb,
            timeout_manager=tm,
        )
        task = Task(
            id="t-1",
            goal="hitl test",
            sub_tasks=[SubTask(id="st-1", description="delete database records")],
        )
        async def reject_after_delay():
            await asyncio.sleep(0.1)
            pending = hitl.get_pending(task_id="t-1")
            if pending:
                hitl.reject(pending[0].id)

        asyncio.create_task(reject_after_delay())
        result = await engine.execute_task(task)
        st_map = {st.id: st for st in result.sub_tasks}
        assert st_map["st-1"].status == TaskState.FAILED.value
        assert "HITL rejected" in st_map["st-1"].error
        engine.close()

    @pytest.mark.asyncio
    async def test_hitl_approval_completes_subtask(self):
        store = TaskStore()
        bus = EventBus()
        hitl = HITLManager(auto_approve_actions=set())
        cb = CircuitBreaker()
        tm = TimeoutManager()
        engine = TaskExecutionEngine(
            task_store=store,
            event_bus=bus,
            hitl_manager=hitl,
            circuit_breaker=cb,
            timeout_manager=tm,
        )
        task = Task(
            id="t-1",
            goal="hitl approve test",
            sub_tasks=[SubTask(id="st-1", description="deploy to production")],
        )
        async def approve_after_delay():
            await asyncio.sleep(0.1)
            pending = hitl.get_pending(task_id="t-1")
            if pending:
                hitl.approve(pending[0].id)

        asyncio.create_task(approve_after_delay())
        result = await engine.execute_task(task)
        assert result.status == TaskState.COMPLETED.value
        engine.close()
