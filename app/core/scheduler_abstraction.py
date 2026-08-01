"""Scheduler abstraction layer with multi-agent extension support.

Provides abstract interfaces for task scheduling, agent communication,
and workload distribution. Designed to support future multi-agent scaling.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable

from app.core.task_state_machine import TaskState

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    """Roles that agents can assume in a multi-agent system."""

    ORCHESTRATOR = "orchestrator"
    WORKER = "worker"
    PLANNER = "planner"
    REVIEWER = "reviewer"
    EXECUTOR = "executor"
    RESEARCHER = "researcher"
    CRITIC = "critic"


class TaskPriority(int, Enum):
    """Task priority levels."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AgentInfo:
    """Information about a registered agent."""

    agent_id: str
    role: AgentRole
    capabilities: list[str] = field(default_factory=list)
    is_available: bool = True
    current_task_id: str | None = None
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    avg_task_duration_ms: float = 0.0
    registered_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScheduledTask:
    """A task in the scheduler queue."""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    description: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    state: TaskState = TaskState.PENDING
    assigned_agent_id: str | None = None
    parent_task_id: str | None = None
    subtask_ids: list[str] = field(default_factory=list)
    result: str | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    timeout_seconds: float = 300.0
    max_retries: int = 2
    retry_count: int = 0
    required_capabilities: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.completed_at or time.time()
        return (end - self.started_at) * 1000


class TaskChannel(ABC):
    """Abstract channel for inter-agent communication."""

    @abstractmethod
    async def send(self, sender_id: str, receiver_id: str, message: dict[str, Any]) -> None:
        """Send a message to another agent."""
        ...

    @abstractmethod
    async def receive(self, agent_id: str) -> dict[str, Any] | None:
        """Receive a message for an agent."""
        ...

    @abstractmethod
    async def broadcast(self, sender_id: str, message: dict[str, Any]) -> None:
        """Broadcast a message to all agents."""
        ...


class InMemoryTaskChannel(TaskChannel):
    """In-memory implementation of task channel for single-process mode."""

    def __init__(self) -> None:
        self._queues: dict[str, list[dict[str, Any]]] = {}
        self._broadcast_queue: list[dict[str, Any]] = []

    async def send(self, sender_id: str, receiver_id: str, message: dict[str, Any]) -> None:
        message["sender_id"] = sender_id
        message["timestamp"] = time.time()
        self._queues.setdefault(receiver_id, []).append(message)

    async def receive(self, agent_id: str) -> dict[str, Any] | None:
        queue = self._queues.get(agent_id, [])
        if queue:
            return queue.pop(0)
        return None

    async def broadcast(self, sender_id: str, message: dict[str, Any]) -> None:
        message["sender_id"] = sender_id
        message["timestamp"] = time.time()
        message["is_broadcast"] = True
        self._broadcast_queue.append(message)

    async def get_broadcasts(self) -> list[dict[str, Any]]:
        messages = list(self._broadcast_queue)
        self._broadcast_queue.clear()
        return messages


class SchedulerBackend(ABC):
    """Abstract scheduler backend for task execution."""

    @abstractmethod
    async def submit(self, task: ScheduledTask, agent_id: str) -> bool:
        """Submit a task for execution."""
        ...

    @abstractmethod
    async def cancel(self, task_id: str) -> bool:
        """Cancel a running task."""
        ...

    @abstractmethod
    async def get_status(self, task_id: str) -> TaskState | None:
        """Get the current state of a task."""
        ...


class MultiAgentScheduler:
    """Scheduler with multi-agent support.

    Supports task distribution, agent registration, and workload balancing.
    """

    def __init__(
        self,
        channel: TaskChannel | None = None,
        max_concurrent_tasks: int = 10,
    ) -> None:
        self._agents: dict[str, AgentInfo] = {}
        self._tasks: dict[str, ScheduledTask] = {}
        self._channel = channel or InMemoryTaskChannel()
        self._max_concurrent = max_concurrent_tasks
        self._semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self._task_handlers: dict[str, Callable[..., Awaitable[str]]] = {}
        self._running_tasks: dict[str, asyncio.Task] = {}

    def register_agent(self, info: AgentInfo) -> None:
        """Register an agent with the scheduler."""
        self._agents[info.agent_id] = info
        logger.info("Registered agent: %s (role: %s)", info.agent_id, info.role.value)

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def get_agent(self, agent_id: str) -> AgentInfo | None:
        """Get agent info."""
        return self._agents.get(agent_id)

    def list_agents(
        self, role: AgentRole | None = None, available_only: bool = False
    ) -> list[AgentInfo]:
        """List registered agents."""
        agents = list(self._agents.values())
        if role:
            agents = [a for a in agents if a.role == role]
        if available_only:
            agents = [a for a in agents if a.is_available]
        return agents

    def register_task_handler(
        self, task_type: str, handler: Callable[..., Awaitable[str]]
    ) -> None:
        """Register a handler for a task type."""
        self._task_handlers[task_type] = handler

    async def submit_task(
        self,
        description: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        required_capabilities: list[str] | None = None,
        payload: dict[str, Any] | None = None,
        parent_task_id: str | None = None,
    ) -> ScheduledTask:
        """Submit a task for execution."""
        task = ScheduledTask(
            description=description,
            priority=priority,
            required_capabilities=required_capabilities or [],
            payload=payload or {},
            parent_task_id=parent_task_id,
        )
        self._tasks[task.task_id] = task

        if parent_task_id and parent_task_id in self._tasks:
            self._tasks[parent_task_id].subtask_ids.append(task.task_id)

        asyncio.create_task(self._schedule_task(task))
        return task

    async def _schedule_task(self, task: ScheduledTask) -> None:
        """Find an agent and execute a task."""
        agent = self._find_best_agent(task)
        if agent is None:
            logger.warning("No available agent for task %s", task.task_id)
            task.state = TaskState.PENDING
            return

        task.assigned_agent_id = agent.agent_id
        task.state = TaskState.ASSIGNED
        agent.is_available = False
        agent.current_task_id = task.task_id

        async with self._semaphore:
            task.state = TaskState.RUNNING
            task.started_at = time.time()

            try:
                handler = self._task_handlers.get(
                    task.payload.get("task_type", "default")
                )
                if handler is None:
                    handler = self._task_handlers.get("default")

                if handler:
                    result = await asyncio.wait_for(
                        handler(task.description, **task.payload),
                        timeout=task.timeout_seconds,
                    )
                    task.result = result
                    task.state = TaskState.COMPLETED
                    agent.total_tasks_completed += 1
                else:
                    task.error = "No handler registered for task type"
                    task.state = TaskState.FAILED
                    agent.total_tasks_failed += 1

            except asyncio.TimeoutError:
                task.error = f"Task timed out after {task.timeout_seconds}s"
                task.state = TaskState.FAILED
                agent.total_tasks_failed += 1
            except Exception as e:
                task.error = str(e)
                task.state = TaskState.FAILED
                agent.total_tasks_failed += 1
                logger.exception("Task %s failed", task.task_id)
            finally:
                task.completed_at = time.time()
                agent.current_task_id = None
                agent.is_available = True

    def _find_best_agent(self, task: ScheduledTask) -> AgentInfo | None:
        """Find the best available agent for a task."""
        available = [a for a in self._agents.values() if a.is_available]
        if not available:
            return None

        if task.required_capabilities:
            capable = [
                a
                for a in available
                if all(c in a.capabilities for c in task.required_capabilities)
            ]
            if capable:
                available = capable

        return min(available, key=lambda a: a.total_tasks_completed)

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        task = self._tasks.get(task_id)
        if task is None:
            return False
        if task.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
            return False

        task.state = TaskState.CANCELLED
        task.completed_at = time.time()

        if task.assigned_agent_id and task.assigned_agent_id in self._agents:
            agent = self._agents[task.assigned_agent_id]
            agent.is_available = True
            agent.current_task_id = None

        if task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()

        return True

    async def decompose_and_schedule(
        self,
        description: str,
        subtasks: list[str],
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> tuple[ScheduledTask, list[ScheduledTask]]:
        """Create a parent task and schedule subtasks."""
        parent = ScheduledTask(
            description=description,
            priority=priority,
        )
        self._tasks[parent.task_id] = parent

        children: list[ScheduledTask] = []
        for subtask_desc in subtasks:
            child = ScheduledTask(
                description=subtask_desc,
                priority=priority,
                parent_task_id=parent.task_id,
            )
            self._tasks[child.task_id] = child
            parent.subtask_ids.append(child.task_id)
            children.append(child)
            asyncio.create_task(self._schedule_task(child))

        return parent, children

    async def wait_for_task(
        self, task_id: str, timeout: float = 300.0
    ) -> ScheduledTask | None:
        """Wait for a task to complete."""
        start = time.time()
        while time.time() - start < timeout:
            task = self._tasks.get(task_id)
            if task and task.state in (
                TaskState.COMPLETED,
                TaskState.FAILED,
                TaskState.CANCELLED,
            ):
                return task
            await asyncio.sleep(0.1)
        return self._tasks.get(task_id)

    def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """Get task status."""
        task = self._tasks.get(task_id)
        if task is None:
            return None
        return {
            "task_id": task.task_id,
            "state": task.state.value,
            "assigned_agent": task.assigned_agent_id,
            "duration_ms": task.duration_ms,
            "result": task.result,
            "error": task.error,
        }

    def get_scheduler_stats(self) -> dict[str, Any]:
        """Get scheduler statistics."""
        states: dict[str, int] = {}
        for task in self._tasks.values():
            states[task.state.value] = states.get(task.state.value, 0) + 1

        return {
            "total_agents": len(self._agents),
            "available_agents": sum(1 for a in self._agents.values() if a.is_available),
            "total_tasks": len(self._tasks),
            "task_states": states,
            "max_concurrent": self._max_concurrent,
            "channel_type": type(self._channel).__name__,
        }
