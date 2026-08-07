"""Event module: push - Event handling and messaging."""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum
from typing import Any
from uuid import uuid4

import structlog

logger = structlog.get_logger()


class PushEventType(StrEnum):
    """Event type enum."""
    CREATED = 'created'
    UPDATED = 'updated'
    DELETED = 'deleted'
    ACTIVATED = 'activated'
    DEACTIVATED = 'deactivated'
    ARCHIVED = 'archived'
    RESTORED = 'restored'


class PushPriority(int, Enum):
    """Event priority."""
    LOW = 1
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


@dataclass
class PushEvent:
    """Domain event."""
    id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = ''
    entity_type: str = ''
    entity_id: str = ''
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    priority: int = 5
    timestamp: datetime = field(default_factory=datetime.utcnow)
    actor: str = ''
    correlation_id: str = ''
    causation_id: str = ''


@dataclass
class PushSubscription:
    """Event subscription."""
    id: str = field(default_factory=lambda: str(uuid4()))
    event_types: list[str] = field(default_factory=list)
    handler: Callable | None = None
    filter_fn: Callable | None = None
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


class PushEventBus:
    """Event bus for publish/subscribe."""

    def __init__(self, max_queue_size: int = 10000):
        self._subscriptions: dict[str, list[PushSubscription]] = defaultdict(list)
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._history: deque = deque(maxlen=1000)
        self._running = False
        self._processed_count = 0
        self._error_count = 0

    def subscribe(
        self,
        event_types: list[str],
        handler: Callable,
        filter_fn: Callable | None = None,
    ) -> str:
        """Subscribe to events."""
        subscription = PushSubscription(
            event_types=event_types,
            handler=handler,
            filter_fn=filter_fn,
        )
        for event_type in event_types:
            self._subscriptions[event_type].append(subscription)
        return subscription.id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove subscription."""
        for event_type, subs in self._subscriptions.items():
            self._subscriptions[event_type] = [s for s in subs if s.id != subscription_id]
        return True

    async def publish(self, event: PushEvent) -> None:
        """Publish event."""
        await self._event_queue.put(event)
        self._history.append(event)

    async def start(self) -> None:
        """Start processing events."""
        self._running = True
        while self._running:
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self._process_event(event)
                self._processed_count += 1
            except TimeoutError:
                continue
            except Exception as e:
                self._error_count += 1
                logger.error(f'Event processing error: {e}')

    async def _process_event(self, event: PushEvent) -> None:
        """Process single event."""
        subscriptions = self._subscriptions.get(event.event_type, [])
        for subscription in subscriptions:
            if not subscription.active:
                continue
            if subscription.filter_fn and not subscription.filter_fn(event):
                continue
            try:
                if asyncio.iscoroutinefunction(subscription.handler):
                    await subscription.handler(event)
                else:
                    subscription.handler(event)
            except Exception as e:
                logger.error(f'Handler error: {e}')

    def stop(self) -> None:
        """Stop processing."""
        self._running = False

    def get_history(
        self, event_type: str | None = None, limit: int = 100
    ) -> list[PushEvent]:
        """Get event history."""
        events = list(self._history)
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Get bus stats."""
        return {
            'processed': self._processed_count,
            'errors': self._error_count,
            'queue_size': self._event_queue.qsize(),
            'subscriptions': sum(len(subs) for subs in self._subscriptions.values()),
        }
