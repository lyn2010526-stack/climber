"""EventBus - decoupled pub/sub event system for inter-component communication.

"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


@dataclass
class Event:
    event_type: str
    data: dict[str, Any]
    source: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = ""


class EventBus:
    """Async pub/sub event bus for decoupled component communication.

    Features:
    - Multiple subscribers per event type
    - Wildcard subscribers (* for all events)
    - Async and sync handlers
    - Event history with configurable limit
    """

    def __init__(self, max_history: int = 1000):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._wildcards: list[Callable] = []
        self._history: list[Event] = []
        self._max_history = max_history
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to a specific event type."""
        self._subscribers[event_type].append(handler)
        logger.debug("subscribed", event_type=event_type, handler=handler.__name__)

    def subscribe_all(self, handler: Callable) -> None:
        """Subscribe to all events (wildcard)."""
        self._wildcards.append(handler)
        logger.debug("subscribed_all", handler=handler.__name__)

    def unsubscribe(self, event_type: str, handler: Callable) -> bool:
        """Unsubscribe from an event type."""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)
            return True
        if handler in self._wildcards:
            self._wildcards.remove(handler)
            return True
        return False

    async def publish(self, event_type: str, data: dict[str, Any], source: str = "") -> None:
        """Publish an event to all subscribers."""
        event = Event(event_type=event_type, data=data, source=source)
        async with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

        handlers = list(self._subscribers.get(event_type, []))
        for handler in self._wildcards:
            handlers.append(handler)

        if not handlers:
            return

        coros = []
        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result) or asyncio.isfuture(result):
                    coros.append(result)
                else:
                    asyncio.create_task(self._run_sync(handler, event))
            except Exception as e:
                logger.error("event_handler_error", event_type=event_type, error=str(e))

        if coros:
            await asyncio.gather(*coros, return_exceptions=True)

        logger.debug("published", event_type=event_type, handlers=len(handlers))

    async def _run_sync(self, handler: Callable, event: Event) -> None:
        try:
            handler(event)
        except Exception as e:
            logger.error("sync_event_handler_error", error=str(e))

    def get_history(self, event_type: str | None = None, limit: int = 100) -> list[Event]:
        """Get recent events, optionally filtered by type."""
        events = self._history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def clear_history(self) -> None:
        self._history.clear()


# Global singleton
event_bus = EventBus()
