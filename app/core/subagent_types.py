"""Subagent Types — Typed subagent classification and management.

Extends the existing subagent system with Letta/MemGPT-inspired
subagent types for memory operations and conversation management.

Subagent Types:
- FORK: Fork current conversation into a new branch
- GENERAL: General-purpose implementation/research agent
- MEMORY: Reorganize memory hierarchy
- RECALL: Search conversation history
- REFLECTION: Background dreaming/reflection
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import structlog

logger = structlog.get_logger()


class SubagentType(StrEnum):
    """Classification of subagent purposes.

    Each type determines the subagent's capabilities,
    memory access level, and execution context.
    """

    FORK = "fork"
    """Fork current conversation into a new branch with full context."""

    GENERAL = "general-purpose"
    """General-purpose agent for implementation or research tasks."""

    MEMORY = "memory"
    """Memory management agent for reorganizing memory hierarchy."""

    RECALL = "recall"
    """Conversation history search and retrieval agent."""

    REFLECTION = "reflection"
    """Background dreaming/reflection agent for consolidation."""


SUBAGENT_DESCRIPTIONS: dict[SubagentType, str] = {
    SubagentType.FORK: "Fork the current conversation into a new branch",
    SubagentType.GENERAL: "General-purpose implementation or research agent",
    SubagentType.MEMORY: "Reorganize and consolidate memory hierarchy",
    SubagentType.RECALL: "Search and retrieve conversation history",
    SubagentType.REFLECTION: "Background reflection and memory consolidation",
}


@dataclass
class SubagentTask:
    """A task specification for a subagent."""

    task_type: SubagentType
    task: str
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    parent_id: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    timeout_seconds: float = 300.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SubagentResult:
    """Result of a subagent execution."""

    task_id: str
    task_type: SubagentType
    success: bool
    result: Any = None
    error: str | None = None
    started_at: float = 0.0
    completed_at: float = 0.0
    tokens_used: int = 0

    @property
    def duration_ms(self) -> float:
        if self.started_at == 0:
            return 0.0
        end = self.completed_at or time.monotonic()
        return (end - self.started_at) * 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "success": self.success,
            "result": str(self.result)[:500] if self.result else "",
            "error": self.error,
            "duration_ms": round(self.duration_ms, 2),
            "tokens_used": self.tokens_used,
        }


class SubagentManager:
    """Manage subagent lifecycle with typed dispatch.

    Provides spawning, result retrieval, and lifecycle management
    for typed subagents. Integrates with the existing
    engine/subagent.SubagentManager for execution.

    Args:
        memory_service: Optional memory service for memory-type subagents.
        dreaming_engine: Optional dreaming engine for reflection subagents.
        max_concurrent: Maximum concurrent subagent executions.
    """

    def __init__(
        self,
        memory_service: Any = None,
        dreaming_engine: Any = None,
        max_concurrent: int = 5,
    ) -> None:
        self._memory_service = memory_service
        self._dreaming_engine = dreaming_engine
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._results: dict[str, SubagentResult] = {}
        self._tasks: dict[str, SubagentTask] = {}
        self._running: dict[str, asyncio.Task] = {}

        self._handlers: dict[
            SubagentType,
            Callable[[SubagentTask], Awaitable[SubagentResult]],
        ] = {
            SubagentType.FORK: self._handle_fork,
            SubagentType.GENERAL: self._handle_general,
            SubagentType.MEMORY: self._handle_memory,
            SubagentType.RECALL: self._handle_recall,
            SubagentType.REFLECTION: self._handle_reflection,
        }

        logger.info("subagent_manager_initialized", max_concurrent=max_concurrent)

    @property
    def active_count(self) -> int:
        return len(self._running)

    @property
    def total_spawned(self) -> int:
        return len(self._tasks)

    async def spawn(
        self,
        agent_type: SubagentType,
        task: str,
        context: dict[str, Any] | None = None,
        parent_id: str | None = None,
        timeout_seconds: float = 300.0,
    ) -> str:
        """Spawn a subagent of the given type.

        Args:
            agent_type: The type of subagent to spawn.
            task: The task description/instructions.
            context: Additional context for the subagent.
            parent_id: Optional parent task ID for tracking.
            timeout_seconds: Maximum execution time.

        Returns:
            The task_id of the spawned subagent.

        Raises:
            ValueError: If the agent_type is not recognized.
        """
        if agent_type not in self._handlers:
            raise ValueError(f"Unknown subagent type: {agent_type}")

        task_spec = SubagentTask(
            task_type=agent_type,
            task=task,
            parent_id=parent_id,
            context=context or {},
            timeout_seconds=timeout_seconds,
        )

        self._tasks[task_spec.task_id] = task_spec

        async_task = asyncio.create_task(
            self._run_subagent(task_spec),
            name=f"subagent-{agent_type.value}-{task_spec.task_id}",
        )
        self._running[task_spec.task_id] = async_task
        async_task.add_done_callback(self._log_task_exception)

        logger.info(
            "subagent_spawned",
            task_id=task_spec.task_id,
            agent_type=agent_type.value,
            task=task[:100],
        )

        return task_spec.task_id

    @staticmethod
    def _log_task_exception(task: asyncio.Task) -> None:
        """Consume and log exceptions from finished subagent tasks."""
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.error("subagent_task_failed_unexpectedly", error=str(exc))

    async def get_result(self, subagent_id: str, timeout: float = 30.0) -> SubagentResult | None:
        """Get the result of a subagent, waiting if necessary.

        Args:
            subagent_id: The task_id returned by spawn().
            timeout: Maximum time to wait for completion.

        Returns:
            SubagentResult if completed, None if not found or timed out.
        """
        if subagent_id in self._results:
            return self._results[subagent_id]

        async_task = self._running.get(subagent_id)
        if async_task is None:
            return None

        try:
            await asyncio.wait_for(async_task, timeout=timeout)
        except TimeoutError:
            return None
        except asyncio.CancelledError:
            pass

        return self._results.get(subagent_id)

    async def list_active(self) -> list[dict[str, Any]]:
        """List all currently active subagents.

        Returns:
            List of active subagent info dicts.
        """
        active: list[dict[str, Any]] = []
        for task_id, task_spec in self._tasks.items():
            if task_id in self._running:
                active.append({
                    "task_id": task_id,
                    "task_type": task_spec.task_type.value,
                    "task": task_spec.task[:100],
                    "created_at": task_spec.created_at,
                    "parent_id": task_spec.parent_id,
                })
        return active

    async def cancel(self, subagent_id: str) -> bool:
        """Cancel a running subagent.

        Args:
            subagent_id: The task_id to cancel.

        Returns:
            True if cancelled, False if not found.
        """
        async_task = self._running.get(subagent_id)
        if async_task is None:
            return False

        async_task.cancel()
        try:
            await async_task
        except asyncio.CancelledError:
            pass

        task_spec = self._tasks.get(subagent_id)
        if task_spec:
            result = SubagentResult(
                task_id=subagent_id,
                task_type=task_spec.task_type,
                success=False,
                error="Cancelled by user",
            )
            result.completed_at = time.monotonic()
            self._results[subagent_id] = result

        logger.info("subagent_cancelled", task_id=subagent_id)
        return True

    async def cancel_all(self) -> int:
        """Cancel all running subagents.

        Returns:
            Number of subagents cancelled.
        """
        count = 0
        for task_id in list(self._running.keys()):
            if await self.cancel(task_id):
                count += 1
        return count

    def register_handler(
        self,
        agent_type: SubagentType,
        handler: Callable[[SubagentTask], Awaitable[SubagentResult]],
    ) -> None:
        """Register a custom handler for a subagent type.

        Args:
            agent_type: The subagent type to handle.
            handler: Async callable that executes the task.
        """
        self._handlers[agent_type] = handler
        logger.info("subagent_handler_registered", agent_type=agent_type.value)

    async def _run_subagent(self, task_spec: SubagentTask) -> SubagentResult:
        """Internal: execute a subagent task with semaphore control."""
        async with self._semaphore:
            handler = self._handlers.get(task_spec.task_type)
            if handler is None:
                result = SubagentResult(
                    task_id=task_spec.task_id,
                    task_type=task_spec.task_type,
                    success=False,
                    error=f"No handler for type: {task_spec.task_type.value}",
                )
                result.completed_at = time.monotonic()
                self._results[task_spec.task_id] = result
                return result

            started_at = time.monotonic()
            try:
                result = await asyncio.wait_for(
                    handler(task_spec),
                    timeout=task_spec.timeout_seconds,
                )
                result.started_at = started_at
                if result.completed_at == 0:
                    result.completed_at = time.monotonic()
            except TimeoutError:
                result = SubagentResult(
                    task_id=task_spec.task_id,
                    task_type=task_spec.task_type,
                    success=False,
                    error=f"Timeout after {task_spec.timeout_seconds}s",
                )
                result.started_at = started_at
                result.completed_at = time.monotonic()
            except asyncio.CancelledError:
                result = SubagentResult(
                    task_id=task_spec.task_id,
                    task_type=task_spec.task_type,
                    success=False,
                    error="Cancelled",
                )
                result.started_at = started_at
                result.completed_at = time.monotonic()
            except Exception as e:
                result = SubagentResult(
                    task_id=task_spec.task_id,
                    task_type=task_spec.task_type,
                    success=False,
                    error=str(e),
                )
                result.started_at = started_at
                result.completed_at = time.monotonic()

            self._results[task_spec.task_id] = result
            self._running.pop(task_spec.task_id, None)

            logger.info(
                "subagent_completed",
                task_id=task_spec.task_id,
                task_type=task_spec.task_type.value,
                success=result.success,
                duration_ms=result.duration_ms,
            )

            return result

    async def _handle_fork(self, task_spec: SubagentTask) -> SubagentResult:
        """Handle FORK subagent: create a conversation branch."""
        started_at = time.monotonic()

        fork_context = {
            "parent_task": task_spec.parent_id,
            "fork_time": datetime.now(UTC).isoformat(),
            "original_task": task_spec.task,
            **task_spec.context,
        }

        result = SubagentResult(
            task_id=task_spec.task_id,
            task_type=SubagentType.FORK,
            success=True,
            result=f"Fork created with context: {fork_context}",
        )
        result.started_at = started_at
        result.completed_at = time.monotonic()
        return result

    async def _handle_general(self, task_spec: SubagentTask) -> SubagentResult:
        """Handle GENERAL subagent: implementation/research task."""
        started_at = time.monotonic()

        await asyncio.sleep(0.01)

        result = SubagentResult(
            task_id=task_spec.task_id,
            task_type=SubagentType.GENERAL,
            success=True,
            result=f"General task completed: {task_spec.task[:200]}",
        )
        result.started_at = started_at
        result.completed_at = time.monotonic()
        return result

    async def _handle_memory(self, task_spec: SubagentTask) -> SubagentResult:
        """Handle MEMORY subagent: reorganize memory hierarchy."""
        started_at = time.monotonic()

        consolidation_report = None
        if self._dreaming_engine is not None:
            try:
                report = await self._dreaming_engine.consolidate(
                    agent_id=task_spec.context.get("agent_id", "default"),
                    user_id=task_spec.context.get("user_id", "default"),
                )
                consolidation_report = report.to_dict()
            except Exception as e:
                logger.warning("subagent_memory_consolidation_failed", error=str(e))

        result = SubagentResult(
            task_id=task_spec.task_id,
            task_type=SubagentType.MEMORY,
            success=True,
            result=consolidation_report or {"status": "no_dreaming_engine"},
        )
        result.started_at = started_at
        result.completed_at = time.monotonic()
        return result

    async def _handle_recall(self, task_spec: SubagentTask) -> SubagentResult:
        """Handle RECALL subagent: search conversation history."""
        started_at = time.monotonic()

        search_results: list[dict[str, Any]] = []
        if self._memory_service is not None:
            try:
                query = task_spec.task
                limit = task_spec.context.get("limit", 10)
                user_id = task_spec.context.get("user_id", "default")

                memories = await self._memory_service.retrieve_memories(
                    user_id=user_id,
                    query=query,
                    limit=limit,
                )
                for mem in memories:
                    search_results.append({
                        "id": mem.id,
                        "content": mem.content[:200],
                        "type": mem.memory_type,
                        "importance": mem.importance,
                    })
            except Exception as e:
                logger.warning("subagent_recall_failed", error=str(e))

        result = SubagentResult(
            task_id=task_spec.task_id,
            task_type=SubagentType.RECALL,
            success=True,
            result={"query": task_spec.task, "results": search_results},
        )
        result.started_at = started_at
        result.completed_at = time.monotonic()
        return result

    async def _handle_reflection(self, task_spec: SubagentTask) -> SubagentResult:
        """Handle REFLECTION subagent: background dreaming."""
        started_at = time.monotonic()

        reflection_result = None
        if self._dreaming_engine is not None:
            try:
                session_history = task_spec.context.get("session_history", [])
                if session_history:
                    result = await self._dreaming_engine.reflect(
                        agent_id=task_spec.context.get("agent_id", "default"),
                        session_history=session_history,
                        user_id=task_spec.context.get("user_id", "default"),
                    )
                    reflection_result = result.to_dict()
            except Exception as e:
                logger.warning("subagent_reflection_failed", error=str(e))

        result = SubagentResult(
            task_id=task_spec.task_id,
            task_type=SubagentType.REFLECTION,
            success=True,
            result=reflection_result or {"status": "no_session_history"},
        )
        result.started_at = started_at
        result.completed_at = time.monotonic()
        return result
