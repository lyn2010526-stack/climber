"""Task execution engine.

Orchestrates task execution with:
- DAG-based sub-task dependency resolution
- Event-driven state transitions
- HITL approval enforcement
- Timeout and circuit breaker protection
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable

from app.core.execution.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, TimeoutManager
from app.core.execution.event_bus import EventBus, TaskEvent
from app.core.execution.hitl import (
    HITLManager,
    HITLStatusApproved,
    HITLStatusPending,
    HITLStatusRejected,
)
from app.core.execution.task_model import SubTask, Task, TaskStore
from app.core.task_state_machine import TaskState

logger = logging.getLogger(__name__)

SubtaskExecutor = Callable[[SubTask, Task], Any]


class TaskExecutionEngine:
    """Executes tasks with event-driven architecture and safety controls."""

    def __init__(
        self,
        task_store: TaskStore | None = None,
        event_bus: EventBus | None = None,
        hitl_manager: HITLManager | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        timeout_manager: TimeoutManager | None = None,
        subtask_executor: SubtaskExecutor | None = None,
    ):
        self._store = task_store or TaskStore()
        self._event_bus = event_bus or EventBus()
        self._hitl = hitl_manager or HITLManager()
        self._circuit_breaker = circuit_breaker or CircuitBreaker()
        self._timeout = timeout_manager or TimeoutManager()
        self._subtask_executor = subtask_executor or self._default_subtask_executor
        self._running_tasks: dict[str, asyncio.Task] = {}

    async def execute_task(self, task: Task) -> Task:
        """Execute a task and its sub-tasks according to DAG dependencies."""
        if not self._circuit_breaker.allow_request():
            task.status = TaskState.FAILED.value
            task.metadata["failure_reason"] = "circuit_breaker_open"
            self._store.save(task)
            await self._publish_event(EventBus.EVENT_FAILED, task.id, {"reason": "circuit_breaker_open"})
            return task

        task.status = TaskState.RUNNING.value
        task.current_iteration += 1
        self._store.save(task)
        self._timeout.start_task(task.id, task.timeout_seconds)
        await self._publish_event(EventBus.EVENT_STARTED, task.id)

        try:
            result = await self._execute_with_dag(task)
            if result:
                task.status = TaskState.COMPLETED.value
                self._circuit_breaker.record_success()
                self._timeout.complete_task(task.id)
                await self._publish_event(EventBus.EVENT_COMPLETED, task.id)
            else:
                task.status = TaskState.FAILED.value
                self._circuit_breaker.record_failure()
                self._timeout.fail_task(task.id)
                await self._publish_event(EventBus.EVENT_FAILED, task.id)
        except asyncio.TimeoutError:
            task.status = TaskState.FAILED.value
            task.metadata["failure_reason"] = "timeout"
            self._circuit_breaker.record_failure()
            self._timeout.fail_task(task.id)
            await self._publish_event(EventBus.EVENT_FAILED, task.id, {"reason": "timeout"})
        except Exception as e:
            task.status = TaskState.FAILED.value
            task.metadata["failure_reason"] = str(e)
            self._circuit_breaker.record_failure()
            self._timeout.fail_task(task.id)
            await self._publish_event(EventBus.EVENT_FAILED, task.id, {"error": str(e)})
        finally:
            task.metadata["completed_at"] = datetime.now(timezone.utc).isoformat()
            self._store.save(task)
            self._running_tasks.pop(task.id, None)

        return task

    async def _execute_with_dag(self, task: Task) -> bool:
        """Execute sub-tasks respecting DAG dependencies."""
        if not task.sub_tasks:
            return True

        completed: set[str] = set()
        subtask_map = {st.id: st for st in task.sub_tasks}
        remaining = set(subtask_map.keys())

        while remaining:
            if self._timeout.check_timeout(task.id):
                raise asyncio.TimeoutError(f"Task {task.id} exceeded timeout")

            ready = self._get_ready_subtasks(subtask_map, completed, remaining)
            if not ready:
                if remaining:
                    task.metadata["failure_reason"] = "circular_dependency"
                    return False
                break

            for subtask_id in ready:
                subtask = subtask_map[subtask_id]
                subtask.status = TaskState.RUNNING.value
                subtask.started_at = datetime.now(timezone.utc).isoformat()
                self._store.save(task)

                if self._requires_hitl(subtask):
                    hitl_req = self._hitl.create_request(
                        task_id=task.id,
                        action_type="execute_subtask",
                        payload={"subtask_id": subtask.id, "description": subtask.description},
                    )
                    await self._publish_event(
                        EventBus.EVENT_NEEDS_APPROVAL,
                        task.id,
                        {"hitl_request_id": hitl_req.id, "subtask_id": subtask.id},
                    )
                    task.status = TaskState.PAUSED.value
                    self._store.save(task)
                    approved = await self._wait_for_approval(hitl_req.id)
                    if not approved:
                        subtask.status = TaskState.FAILED.value
                        subtask.error = "HITL rejected"
                        completed.add(subtask_id)
                        remaining.discard(subtask_id)
                        continue
                    task.status = TaskState.RUNNING.value
                    self._store.save(task)

                try:
                    result = await asyncio.wait_for(
                        self._run_subtask(subtask, task),
                        timeout=self._timeout.get_remaining_time(task.id),
                    )
                    subtask.result = str(result) if result else ""
                    subtask.status = TaskState.COMPLETED.value
                    subtask.completed_at = datetime.now(timezone.utc).isoformat()
                    completed.add(subtask_id)
                    remaining.discard(subtask_id)
                    await self._publish_event(
                        EventBus.EVENT_SUBTASK_COMPLETED,
                        task.id,
                        {"subtask_id": subtask.id},
                    )
                except asyncio.TimeoutError:
                    subtask.status = TaskState.FAILED.value
                    subtask.error = "timeout"
                    completed.add(subtask_id)
                    remaining.discard(subtask_id)
                    raise
                except Exception as e:
                    subtask.status = TaskState.FAILED.value
                    subtask.error = str(e)
                    completed.add(subtask_id)
                    remaining.discard(subtask_id)

            self._store.save(task)

        return all(
            subtask_map[st_id].status == TaskState.COMPLETED.value
            for st_id in subtask_map
        )

    def _get_ready_subtasks(
        self,
        subtask_map: dict[str, SubTask],
        completed: set[str],
        remaining: set[str],
    ) -> list[str]:
        ready = []
        for st_id in remaining:
            subtask = subtask_map[st_id]
            if all(dep in completed for dep in subtask.dependencies):
                ready.append(st_id)
        return ready

    def _requires_hitl(self, subtask: SubTask) -> bool:
        sensitive_keywords = {"delete", "deploy", "production", "remove", "destroy"}
        desc_lower = subtask.description.lower()
        return any(kw in desc_lower for kw in sensitive_keywords)

    async def _wait_for_approval(self, hitl_request_id: str, poll_interval: float = 0.1) -> bool:
        while True:
            request = self._hitl.get_request(hitl_request_id)
            if not request:
                return False
            if request.status == HITLStatusApproved:
                return True
            if request.status == HITLStatusRejected:
                return False
            expired = self._hitl.expire_pending()
            for exp in expired:
                if exp.id == hitl_request_id:
                    return False
            await asyncio.sleep(poll_interval)

    async def _run_subtask(self, subtask: SubTask, task: Task) -> Any:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._subtask_executor, subtask, task)

    def _default_subtask_executor(self, subtask: SubTask, task: Task) -> str:
        return f"Executed: {subtask.description}"

    async def _publish_event(self, event_type: str, task_id: str, data: dict[str, Any] | None = None) -> None:
        event = TaskEvent(
            event_type=event_type,
            task_id=task_id,
            data=data or {},
        )
        await self._event_bus.publish(event)

    async def pause_task(self, task_id: str) -> Task | None:
        task = self._store.load(task_id)
        if not task:
            return None
        task.status = TaskState.PAUSED.value
        self._store.save(task)
        await self._publish_event(EventBus.EVENT_PAUSED, task_id)
        return task

    async def resume_task(self, task: Task) -> Task:
        await self._publish_event(EventBus.EVENT_RESUMED, task.id)
        return await self.execute_task(task)

    async def cancel_task(self, task_id: str) -> Task | None:
        task = self._store.load(task_id)
        if not task:
            return None
        task.status = TaskState.CANCELLED.value
        self._store.save(task)
        if task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()
        return task

    def close(self) -> None:
        self._store.close()
        self._event_bus.close()
        self._hitl.close()
        self._timeout.close()
