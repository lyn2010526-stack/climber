"""Human-in-the-loop (HITL) interrupt management.

Enables pausing graph execution at designated points to request human input,
review, or approval before continuing.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class Interrupt(BaseModel):
    """An interrupt request awaiting human response.

    Attributes:
        id: Unique interrupt identifier.
        node: Name of the node where execution was paused.
        value: The value/data that triggered the interrupt (for review).
        thread_id: The thread/session this interrupt belongs to.
        checkpoint_id: Associated checkpoint for resuming.
        status: Current status: pending, resolved, expired, cancelled.
        response: The human-provided response value.
        created_at: When the interrupt was created.
        resolved_at: When the interrupt was resolved.
    """

    id: str = Field(default_factory=lambda: f"intr-{uuid.uuid4().hex[:16]}")
    node: str
    value: Any = None
    thread_id: str = "default"
    checkpoint_id: str | None = None
    status: str = "pending"
    response: Any = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HITLManager:
    """Manages human-in-the-loop interrupts across graph executions.

    Supports:
    - Pausing execution at any node
    - Resuming with human-provided values
    - Querying pending interrupts
    - Timeout-based auto-cancellation
    """

    def __init__(self, default_timeout: float | None = None) -> None:
        self._interrupts: dict[str, Interrupt] = {}
        self._pending_events: dict[str, asyncio.Event] = {}
        self._thread_index: dict[str, list[str]] = {}
        self._lock = asyncio.Lock()
        self._default_timeout = default_timeout

    async def interrupt(
        self,
        node: str,
        value: Any = None,
        thread_id: str = "default",
        checkpoint_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Create an interrupt and pause execution.

        Args:
            node: The node requesting the interrupt.
            value: Data for the human to review.
            thread_id: Associated thread/session.
            checkpoint_id: Checkpoint to resume from.
            metadata: Additional context.

        Returns:
            The interrupt ID for later resolution.
        """
        interrupt_obj = Interrupt(
            node=node,
            value=value,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            metadata=metadata or {},
        )
        async with self._lock:
            self._interrupts[interrupt_obj.id] = interrupt_obj
            self._thread_index.setdefault(thread_id, []).append(interrupt_obj.id)
            self._pending_events[interrupt_obj.id] = asyncio.Event()

        logger.info(
            "interrupt_created",
            interrupt_id=interrupt_obj.id,
            node=node,
            thread_id=thread_id,
        )

        if self._default_timeout:
            asyncio.create_task(self._auto_expire(interrupt_obj.id, self._default_timeout))

        return interrupt_obj.id

    async def resume(self, interrupt_id: str, value: Any) -> Interrupt:
        """Resolve an interrupt with a human-provided value.

        Args:
            interrupt_id: The interrupt to resolve.
            value: The human's response value.

        Returns:
            The resolved Interrupt object.

        Raises:
            KeyError: If interrupt_id not found.
            RuntimeError: If interrupt already resolved.
        """
        async with self._lock:
            intr = self._interrupts.get(interrupt_id)
            if not intr:
                raise KeyError(f"Interrupt {interrupt_id} not found")
            if intr.status != "pending":
                raise RuntimeError(
                    f"Interrupt {interrupt_id} already {intr.status}"
                )
            intr.status = "resolved"
            intr.response = value
            intr.resolved_at = datetime.now(UTC)
            event = self._pending_events.get(interrupt_id)

        if event:
            event.set()

        logger.info(
            "interrupt_resolved",
            interrupt_id=interrupt_id,
            node=intr.node,
            thread_id=intr.thread_id,
        )
        return intr

    async def cancel(self, interrupt_id: str) -> Interrupt:
        """Cancel a pending interrupt."""
        async with self._lock:
            intr = self._interrupts.get(interrupt_id)
            if not intr:
                raise KeyError(f"Interrupt {interrupt_id} not found")
            intr.status = "cancelled"
            intr.resolved_at = datetime.now(UTC)
            event = self._pending_events.get(interrupt_id)

        if event:
            event.set()

        logger.info("interrupt_cancelled", interrupt_id=interrupt_id)
        return intr

    async def wait_for(self, interrupt_id: str, timeout: float | None = None) -> Any:
        """Wait for an interrupt to be resolved and return its response.

        Args:
            interrupt_id: The interrupt to wait for.
            timeout: Maximum wait time in seconds.

        Returns:
            The response value from the human.

        Raises:
            asyncio.TimeoutError: If timeout expires before resolution.
        """
        event = self._pending_events.get(interrupt_id)
        if not event:
            raise KeyError(f"No pending event for interrupt {interrupt_id}")
        await asyncio.wait_for(event.wait(), timeout=timeout)

        intr = self._interrupts.get(interrupt_id)
        if intr and intr.status == "resolved":
            return intr.response
        raise RuntimeError(f"Interrupt {interrupt_id} was not resolved successfully")

    async def get_pending(self, thread_id: str | None = None) -> list[Interrupt]:
        """Get pending interrupts, optionally filtered by thread."""
        async with self._lock:
            if thread_id:
                ids = self._thread_index.get(thread_id, [])
                return [
                    self._interrupts[iid]
                    for iid in ids
                    if iid in self._interrupts and self._interrupts[iid].status == "pending"
                ]
            return [
                intr for intr in self._interrupts.values() if intr.status == "pending"
            ]

    async def get(self, interrupt_id: str) -> Interrupt | None:
        """Get an interrupt by ID."""
        return self._interrupts.get(interrupt_id)

    async def _auto_expire(self, interrupt_id: str, timeout: float) -> None:
        """Auto-expire an interrupt after timeout."""
        await asyncio.sleep(timeout)
        async with self._lock:
            intr = self._interrupts.get(interrupt_id)
            if intr and intr.status == "pending":
                intr.status = "expired"
                intr.resolved_at = datetime.now(UTC)
                event = self._pending_events.get(interrupt_id)
                if event:
                    event.set()
                logger.info("interrupt_expired", interrupt_id=interrupt_id)

    @property
    def pending_count(self) -> int:
        return sum(1 for intr in self._interrupts.values() if intr.status == "pending")
