"""Streaming support for Pregel execution.

Provides real-time event streams for:
- State updates after each super-step
- Full state snapshots (values mode)
- Message-level streaming
- Checkpoint events
- Custom events from nodes
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class StreamEventType(StrEnum):
    """Types of stream events."""

    UPDATES = "updates"
    VALUES = "values"
    MESSAGES = "messages"
    CUSTOM = "custom"
    CHECKPOINT = "checkpoint"
    START = "start"
    END = "end"
    ERROR = "error"
    INTERRUPT = "interrupt"
    NODE_START = "node_start"
    NODE_END = "node_end"


class StreamEvent(BaseModel):
    """A single event emitted during graph execution.

    Attributes:
        type: Event type identifier.
        data: Event payload.
        node: Node name associated with this event (if applicable).
        step: Super-step number.
        timestamp: When the event was emitted.
    """

    type: StreamEventType
    data: Any
    node: str | None = None
    step: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "data": self.data,
            "node": self.node,
            "step": self.step,
            "timestamp": self.timestamp.isoformat(),
        }


class StreamManager:
    """Manages streaming output from graph execution.

    Uses an async queue to decouple event producers from consumers,
    supporting multiple concurrent subscribers.
    """

    def __init__(self, max_queue_size: int = 1000) -> None:
        self._queue: asyncio.Queue[StreamEvent | None] = asyncio.Queue(maxsize=max_queue_size)
        self._subscribers: list[asyncio.Queue[StreamEvent | None]] = []
        self._closed = False

    async def emit(self, event: StreamEvent) -> None:
        """Emit an event to all subscribers."""
        if self._closed:
            return
        await self._queue.put(event)
        for queue in tuple(self._subscribers):
            await queue.put(event)

    async def subscribe(self) -> AsyncIterator[StreamEvent]:
        """Subscribe to the event stream. Yields events until stream closes."""
        queue: asyncio.Queue[StreamEvent | None] = asyncio.Queue()
        self._subscribers.append(queue)
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
        finally:
            self._subscribers.remove(queue)

    async def close(self) -> None:
        """Close the stream, signaling all subscribers to stop."""
        if self._closed:
            return
        self._closed = True
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        await self._queue.put(None)
        for queue in tuple(self._subscribers):
            await queue.put(None)

    async def stream_values(
        self,
        initial_input: dict,
        execute_func,
    ) -> AsyncIterator[StreamEvent]:
        """Stream full state values after each super-step.

        Args:
            initial_input: The initial graph input.
            execute_func: Async callable that takes input and yields state dicts.

        Yields:
            StreamEvent with type VALUES containing full state after each step.
        """
        await self.emit(StreamEvent(type=StreamEventType.START, data={"input": initial_input}))
        try:
            async for state in execute_func(initial_input):
                await self.emit(StreamEvent(type=StreamEventType.VALUES, data=state))
        except Exception as e:
            await self.emit(StreamEvent(type=StreamEventType.ERROR, data={"error": str(e)}))
            raise
        finally:
            await self.emit(StreamEvent(type=StreamEventType.END, data={}))
            await self.close()

    async def stream_updates(
        self,
        initial_input: dict,
        execute_func,
    ) -> AsyncIterator[StreamEvent]:
        """Stream incremental updates (delta) after each super-step.

        Args:
            initial_input: The initial graph input.
            execute_func: Async callable that takes input and yields update dicts.

        Yields:
            StreamEvent with type UPDATES containing incremental changes.
        """
        await self.emit(StreamEvent(type=StreamEventType.START, data={"input": initial_input}))
        try:
            async for updates, node, step in execute_func(initial_input):
                await self.emit(
                    StreamEvent(
                        type=StreamEventType.UPDATES,
                        data=updates,
                        node=node,
                        step=step,
                    )
                )
        except Exception as e:
            await self.emit(StreamEvent(type=StreamEventType.ERROR, data={"error": str(e)}))
            raise
        finally:
            await self.emit(StreamEvent(type=StreamEventType.END, data={}))
            await self.close()


async def stream_events(
    execute_func,
    mode: str = "values",
) -> AsyncIterator[StreamEvent]:
    """Convenience function to stream events from an async generator.

    Args:
        execute_func: Async generator yielding (data, node, step) tuples.
        mode: "values" for full state, "updates" for deltas.

    Yields:
        StreamEvent objects.
    """
    event_type = StreamEventType.VALUES if mode == "values" else StreamEventType.UPDATES
    async for data, node, step in execute_func:
        yield StreamEvent(type=event_type, data=data, node=node, step=step)
