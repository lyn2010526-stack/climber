"""Task scheduler with state machine integration.

- LangGraph `StateGraph` + `Pregel` 调度循环
- MonkeyCode `backend/biz/task/` Manager 生命周期管理
- OpenCode task queue 设计
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from app.core.task_state_machine import TaskHook, TaskState, TaskStateMachine


@dataclass
class ScheduledTask:
    """A task scheduled for execution."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    state_machine: TaskStateMachine = field(
        default_factory=lambda: TaskStateMachine(task_id=str(uuid.uuid4()))
    )
    created_at: float = field(default_factory=time.time)
    scheduled_at: float | None = None
    started_at: float | None = None
    finished_at: float | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: str | None = None


TaskRunner = Callable[[ScheduledTask], Coroutine[Any, Any, None]]


class TaskLifecycleManager:
    """Simple task lifecycle manager backed by TaskStateMachine.

    参考 LangGraph Pregel 调度循环：
    - 每个任务独立状态机
    - Hook 链在状态转换时触发
    - 支持任务注册、启动、取消、重试
    """

    def __init__(self):
        self._tasks: dict[str, ScheduledTask] = {}
        self._runners: dict[str, TaskRunner] = {}
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._global_hooks: list[tuple[int, TaskHook]] = []

    def register_runner(self, task_type: str, runner: TaskRunner) -> None:
        self._runners[task_type] = runner

    def add_global_hook(self, priority: int, hook: TaskHook) -> None:
        self._global_hooks.append((priority, hook))
        self._global_hooks.sort(key=lambda x: x[0], reverse=True)

    def submit(self, task_type: str, name: str = "", payload: dict[str, Any] | None = None, scheduled_at: float | None = None) -> ScheduledTask:
        task = ScheduledTask(
            name=name or task_type,
            state_machine=TaskStateMachine(task_id=str(uuid.uuid4())),
            payload=payload or {},
            scheduled_at=scheduled_at,
        )
        self._tasks[task.task_id] = task
        return task

    async def start(self, task_id: str) -> None:
        task = self._tasks.get(task_id)
        if not task:
            raise KeyError(f"Task {task_id} not found")
        if task.state_machine.state != TaskState.PENDING:
            return
        runner = self._runners.get(task.name)
        if runner is None:
            raise ValueError(f"No runner registered for task type {task.name}")
        await task.state_machine.transition(TaskState.PROCESSING, trigger="scheduler_start")
        task.started_at = time.time()
        coro = self._wrap_runner(task, runner)
        asyncio_task = asyncio.create_task(coro)
        self._running_tasks[task_id] = asyncio_task

    async def cancel(self, task_id: str) -> None:
        task = self._tasks.get(task_id)
        if not task:
            return
        asyncio_task = self._running_tasks.get(task_id)
        if asyncio_task and not asyncio_task.done():
            asyncio_task.cancel()
            try:
                await asyncio_task
            except asyncio.CancelledError:
                pass
        if task.state_machine.state in (TaskState.PENDING, TaskState.PROCESSING):
            await task.state_machine.transition(TaskState.CANCELLED, trigger="scheduler_cancel")
        task.finished_at = time.time()

    def get_task(self, task_id: str) -> ScheduledTask | None:
        return self._tasks.get(task_id)

    def list_tasks(self, state: TaskState | None = None) -> list[ScheduledTask]:
        tasks = list(self._tasks.values())
        if state is not None:
            tasks = [t for t in tasks if t.state_machine.state == state]
        return tasks

    async def _wrap_runner(self, task: ScheduledTask, runner: TaskRunner) -> None:
        try:
            await runner(task)
            if task.state_machine.state == TaskState.PROCESSING:
                await task.state_machine.transition(TaskState.COMPLETED, trigger="runner_complete")
        except asyncio.CancelledError:
            await task.state_machine.transition(TaskState.CANCELLED, trigger="runner_cancelled")
        except Exception as e:
            task.error = str(e)
            if task.state_machine.state == TaskState.PROCESSING:
                await task.state_machine.transition(TaskState.FAILED, trigger="runner_error")
        finally:
            task.finished_at = time.time()
            self._running_tasks.pop(task.task_id, None)
