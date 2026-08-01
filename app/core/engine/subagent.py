"""Subagent lifecycle manager — reference: OpenSquilla SubagentManager.

Features:
- Depth limit (default 3) — prevents unbounded recursion
- Concurrency limit (default 5) — caps parallel sub-agents
- Orphan cleanup — detects and terminates stale runs
- Per-member token/cost tracking
- Cascade cancellation — parent cancellation propagates to children
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Protocol

import structlog

logger = structlog.get_logger()

logger = structlog.get_logger()


class SubagentState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ORPHANED = "orphaned"
    TIMED_OUT = "timed_out"


@dataclass
class SubagentSpec:
    """Specification for a sub-agent task."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    description: str = ""
    model: str = ""
    provider: str = ""
    api_key: str = ""
    base_url: str | None = None
    system_prompt: str = ""
    tools: list[str] = field(default_factory=list)
    timeout_seconds: float = 120.0
    parent_id: str | None = None
    depth: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SubagentUsage:
    """Token and cost tracking for a single sub-agent."""
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    tool_calls: int = 0
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_usd": round(self.cost_usd, 6),
            "tool_calls": self.tool_calls,
            "duration_ms": round(self.duration_ms, 2),
        }


@dataclass
class SubagentRecord:
    """Full record of a sub-agent execution."""
    spec: SubagentSpec
    state: SubagentState = SubagentState.PENDING
    usage: SubagentUsage = field(default_factory=SubagentUsage)
    result: str = ""
    error: str | None = None
    created_at: float = field(default_factory=time.monotonic)
    started_at: float | None = None
    completed_at: float | None = None
    child_ids: list[str] = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.completed_at or time.monotonic()
        return (end - self.started_at) * 1000

    @property
    def is_active(self) -> bool:
        return self.state in (SubagentState.PENDING, SubagentState.RUNNING)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.spec.task_id,
            "state": self.state.value,
            "depth": self.spec.depth,
            "parent_id": self.spec.parent_id,
            "usage": self.usage.to_dict(),
            "result": self.result[:200] if self.result else "",
            "error": self.error,
            "duration_ms": round(self.duration_ms, 2),
            "child_ids": self.child_ids,
        }


class SubagentManager:
    """Manages sub-agent lifecycle with depth limits, concurrency control, and cleanup.

    Reference: OpenSquilla SubagentManager — depth_limit=3, concurrency_limit=5.
    """

    def __init__(
        self,
        *,
        depth_limit: int = 3,
        concurrency_limit: int = 5,
        orphan_timeout: float = 300.0,
        enable_cascade_cancel: bool = True,
    ):
        self._depth_limit = depth_limit
        self._concurrency_limit = concurrency_limit
        self._orphan_timeout = orphan_timeout
        self._enable_cascade_cancel = enable_cascade_cancel

        self._records: dict[str, SubagentRecord] = {}
        self._semaphore = asyncio.Semaphore(concurrency_limit)
        self._running_count = 0
        self._cancel_events: dict[str, asyncio.Event] = {}

    @property
    def active_count(self) -> int:
        return sum(1 for r in self._records.values() if r.is_active)

    @property
    def total_count(self) -> int:
        return len(self._records)

    def get_record(self, task_id: str) -> SubagentRecord | None:
        return self._records.get(task_id)

    def get_children(self, parent_id: str) -> list[SubagentRecord]:
        parent = self._records.get(parent_id)
        if not parent:
            return []
        return [self._records[cid] for cid in parent.child_ids if cid in self._records]

    def get_active_runs(self) -> list[SubagentRecord]:
        return [r for r in self._records.values() if r.is_active]

    async def spawn(
        self,
        spec: SubagentSpec,
        runner: Callable[[SubagentSpec], Awaitable[tuple[str, SubagentUsage]]],
    ) -> SubagentRecord:
        """Spawn a new sub-agent with depth and concurrency control.

        Args:
            spec: Sub-agent specification
            runner: Async callable that executes the task and returns (result, usage)

        Returns:
            SubagentRecord with final state

        Raises:
            DepthLimitExceeded: If spec.depth >= depth_limit
            ConcurrencyLimitExceeded: If too many concurrent runs
        """
        if spec.depth >= self._depth_limit:
            record = SubagentRecord(
                spec=spec,
                state=SubagentState.FAILED,
                error=f"Depth limit ({self._depth_limit}) exceeded",
            )
            self._records[spec.task_id] = record
            return record

        record = SubagentRecord(spec=spec, state=SubagentState.PENDING)
        self._records[spec.task_id] = record
        self._cancel_events[spec.task_id] = asyncio.Event()

        # Register as child of parent
        if spec.parent_id and spec.parent_id in self._records:
            parent = self._records[spec.parent_id]
            parent.child_ids.append(spec.task_id)

        # Acquire concurrency slot
        acquired = self._semaphore.locked()
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=5.0)
        except asyncio.TimeoutError:
            record.state = SubagentState.FAILED
            record.error = "Concurrency acquisition timeout"
            return record

        self._running_count += 1
        record.state = SubagentState.RUNNING
        record.started_at = time.monotonic()

        try:
            result, usage = await asyncio.wait_for(
                self._run_with_cancel(spec, runner),
                timeout=spec.timeout_seconds,
            )
            record.result = result
            record.usage = usage
            record.state = SubagentState.COMPLETED
        except asyncio.TimeoutError:
            record.state = SubagentState.TIMED_OUT
            record.error = f"Timeout after {spec.timeout_seconds}s"
        except asyncio.CancelledError:
            record.state = SubagentState.CANCELLED
            record.error = "Cancelled by parent"
        except Exception as e:
            record.state = SubagentState.FAILED
            record.error = str(e)
        finally:
            record.completed_at = time.monotonic()
            self._semaphore.release()
            self._running_count -= 1

        return record

    async def _run_with_cancel(
        self,
        spec: SubagentSpec,
        runner: Callable[[SubagentSpec], Awaitable[tuple[str, SubagentUsage]]],
    ) -> tuple[str, SubagentUsage]:
        """Run task with cancellation support."""
        cancel_event = self._cancel_events.get(spec.task_id)
        if cancel_event is None:
            return await runner(spec)

        # Create a task that can be cancelled
        task = asyncio.create_task(runner(spec))
        cancel_task = asyncio.create_task(cancel_event.wait())

        done, pending = await asyncio.wait(
            {task, cancel_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        for p in pending:
            p.cancel()

        if task in done:
            return task.result()
        else:
            raise asyncio.CancelledError()

    def cancel(self, task_id: str) -> bool:
        """Cancel a running sub-agent and optionally cascade to children."""
        record = self._records.get(task_id)
        if not record or not record.is_active:
            return False

        cancel_event = self._cancel_events.get(task_id)
        if cancel_event:
            cancel_event.set()

        if self._enable_cascade_cancel:
            for child_id in record.child_ids:
                self.cancel(child_id)

        return True

    async def cleanup_orphans(self) -> list[str]:
        """Detect and mark orphaned sub-agents.

        An orphan is a RUNNING sub-agent whose parent is no longer active
        and has exceeded the orphan timeout.

        Returns:
            List of orphaned task IDs
        """
        orphaned: list[str] = []
        now = time.monotonic()

        for record in self._records.values():
            if record.state != SubagentState.RUNNING:
                continue

            spec = record.spec
            if spec.parent_id is None:
                continue

            parent = self._records.get(spec.parent_id)
            if parent and parent.is_active:
                continue

            # Parent is not active — check timeout
            elapsed = now - (record.started_at or now)
            if elapsed > self._orphan_timeout:
                record.state = SubagentState.ORPHANED
                record.error = f"Orphaned (parent {spec.parent_id} inactive, timeout {elapsed:.0f}s)"
                record.completed_at = now
                orphaned.append(spec.task_id)
                logger.warning("subagent.orphaned", task_id=spec.task_id, parent_id=spec.parent_id)

        return orphaned

    def get_stats(self) -> dict[str, Any]:
        """Get sub-agent manager statistics."""
        states: dict[str, int] = {}
        total_tokens = 0
        total_cost = 0.0
        total_duration = 0.0
        completed = 0

        for r in self._records.values():
            states[r.state.value] = states.get(r.state.value, 0) + 1
            total_tokens += r.usage.tokens_in + r.usage.tokens_out
            total_cost += r.usage.cost_usd
            if r.state == SubagentState.COMPLETED:
                completed += 1
                total_duration += r.duration_ms

        return {
            "total": len(self._records),
            "active": self.active_count,
            "states": states,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 6),
            "avg_duration_ms": round(total_duration / max(completed, 1), 2),
            "depth_limit": self._depth_limit,
            "concurrency_limit": self._concurrency_limit,
        }


class DepthLimitExceeded(Exception):
    """Raised when sub-agent depth limit is exceeded."""
    pass


class ConcurrencyLimitExceeded(Exception):
    """Raised when concurrency limit is reached."""
    pass
