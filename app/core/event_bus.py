"""Event Bus — unified pub/sub event system for middleware and components.

Provides:
- Pub/sub pattern for decoupled event handling
- Event filtering by type
- Event history for debugging
- Middleware event hooks
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class EventSubscription:
    """A subscription to an event type."""
    callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
    event_type: str | None = None  # None = all events
    filter_fn: Callable[[dict[str, Any]], bool] | None = None


class EventBus:
    """Unified event bus for pub/sub event handling.

    Usage:
        bus = EventBus()
        bus.subscribe("tool_result", my_handler)
        await bus.publish("tool_result", {"tool": "ls", "output": "..."})
    """

    def __init__(self, history_size: int = 100):
        self._subscribers: dict[str, list[EventSubscription]] = defaultdict(list)
        self._global_subscribers: list[EventSubscription] = []
        self._history: list[dict[str, Any]] = []
        self._history_size = history_size

    def subscribe(
        self,
        event_type: str | None,
        callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
        filter_fn: Callable[[dict[str, Any]], bool] | None = None,
    ) -> None:
        """Subscribe to an event type.

        Args:
            event_type: Event type to subscribe to (None for all events)
            callback: Async callback function
            filter_fn: Optional filter function
        """
        sub = EventSubscription(callback=callback, event_type=event_type, filter_fn=filter_fn)
        if event_type is None:
            self._global_subscribers.append(sub)
        else:
            self._subscribers[event_type].append(sub)

    def unsubscribe(
        self,
        event_type: str | None,
        callback: Callable,
    ) -> None:
        """Remove a subscription."""
        if event_type is None:
            self._global_subscribers = [
                s for s in self._global_subscribers if s.callback != callback
            ]
        else:
            self._subscribers[event_type] = [
                s for s in self._subscribers[event_type] if s.callback != callback
            ]

    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event to all subscribers.

        Args:
            event_type: Type of event
            data: Event data
        """
        event = {"type": event_type, **data}

        # Record in history
        self._history.append(event)
        if len(self._history) > self._history_size:
            self._history = self._history[-self._history_size:]

        # Notify type-specific subscribers
        for sub in self._subscribers.get(event_type, []):
            if sub.filter_fn and not sub.filter_fn(event):
                continue
            try:
                await sub.callback(event)
            except Exception as e:
                logger.warning(
                    "event_bus.subscriber_error",
                    event_type=event_type,
                    error=str(e),
                )

        # Notify global subscribers
        for sub in self._global_subscribers:
            if sub.event_type and sub.event_type != event_type:
                continue
            if sub.filter_fn and not sub.filter_fn(event):
                continue
            try:
                await sub.callback(event)
            except Exception as e:
                logger.warning(
                    "event_bus.subscriber_error",
                    event_type=event_type,
                    error=str(e),
                )

    def get_history(
        self,
        event_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get event history, optionally filtered by type."""
        if event_type:
            events = [e for e in self._history if e.get("type") == event_type]
        else:
            events = self._history
        return events[-limit:]

    def clear_history(self) -> None:
        """Clear event history."""
        self._history.clear()


# Global event bus instance
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
