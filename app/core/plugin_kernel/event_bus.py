"""Typed event bus with pub/sub, request-response, and append-only logging.

Supports three interaction modes required by the plugin kernel:
- subscribe / publish (fire-and-forget broadcast)
- request / response (caller awaits a handler's reply)
- every published event is appended to an append-only trace log when a
  log sink is installed.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

import structlog

logger = structlog.get_logger()

Handler = Callable[[dict[str, Any]], Coroutine[Any, Any, Any]]
RequestHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, Any]]


class EventBusError(RuntimeError):
    """Raised when an event operation fails (e.g. no request handler)."""


class TypedEventBus:
    """Typed event bus supporting pub/sub and request-response.

    Args:
        trace_sink: optional async callable ``async def sink(event: dict) -> None``
            that receives every published event for append-only persistence.
    """

    def __init__(self, trace_sink: Callable[[dict[str, Any]], Coroutine[Any, Any, None]] | None = None):
        self._subscribers: dict[str, list[tuple[Handler, str]]] = defaultdict(list)
        self._request_handlers: dict[str, tuple[RequestHandler, str]] = {}
        self._trace_sink = trace_sink
        self._history: list[dict[str, Any]] = []
        self._history_size = 200

    # ── pub/sub ──

    def subscribe(
        self, event_type: str, handler: Handler, owner: str = ""
    ) -> None:
        self._subscribers[event_type].append((handler, owner))

    def unsubscribe(self, event_type: str, handler: Handler) -> None:
        handlers = self._subscribers.get(event_type, [])
        self._subscribers[event_type] = [
            (h, o) for (h, o) in handlers if h != handler
        ]

    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        event = {
            "id": str(uuid.uuid4()),
            "type": event_type,
            "ts": time.time(),
            **data,
        }
        self._history.append(event)
        if len(self._history) > self._history_size:
            self._history = self._history[-self._history_size:]

        if self._trace_sink is not None:
            try:
                await self._trace_sink(event)
            except Exception as exc:  # logging must never break dispatch
                logger.warning("event_bus.trace_sink_failed", error=str(exc), event_type=event_type)

        for handler, _owner in list(self._subscribers.get(event_type, [])):
            try:
                await handler(event)
            except Exception as exc:
                logger.warning(
                    "event_bus.handler_error",
                    event_type=event_type,
                    error=str(exc),
                )

    # ── request / response ──

    def register_request_handler(
        self, request_type: str, handler: RequestHandler, owner: str = ""
    ) -> None:
        self._request_handlers[request_type] = (handler, owner)

    def unregister_request_handler(self, request_type: str, owner: str = "") -> None:
        existing = self._request_handlers.get(request_type)
        if existing is not None and (not owner or existing[1] == owner):
            self._request_handlers.pop(request_type, None)

    async def request(self, request_type: str, payload: dict[str, Any]) -> Any:
        """Dispatch a request and await the registered handler's response.

        Raises EventBusError when no handler is registered for the type.
        """
        handler, _owner = self._request_handlers.get(request_type) or (None, "")
        if handler is None:
            raise EventBusError(f"no request handler registered for '{request_type}'")
        event = {
            "id": str(uuid.uuid4()),
            "type": f"request:{request_type}",
            "ts": time.time(),
            **payload,
        }
        self._history.append(event)
        if self._trace_sink is not None:
            try:
                await self._trace_sink(event)
            except Exception as exc:
                logger.warning("event_bus.trace_sink_failed", error=str(exc), request_type=request_type)
        try:
            response = await handler(payload)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("event_bus.request_handler_error", request_type=request_type, error=str(exc))
            raise EventBusError(f"request handler '{request_type}' failed: {exc}") from exc
        response_event = {
            "id": str(uuid.uuid4()),
            "type": f"response:{request_type}",
            "ts": time.time(),
            "ok": True,
            "value": response,
        }
        self._history.append(response_event)
        if self._trace_sink is not None:
            try:
                await self._trace_sink(response_event)
            except Exception as exc:
                logger.warning("event_bus.trace_sink_failed", error=str(exc), request_type=request_type)
        return response

    # ── introspection ──

    def get_history(
        self, event_type: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        events = self._history
        if event_type:
            events = [e for e in events if e.get("type") == event_type]
        return events[-limit:]

    def clear_history(self) -> None:
        self._history.clear()

    def subscription_count(self, event_type: str) -> int:
        return len(self._subscribers.get(event_type, []))

    def request_handler_count(self) -> int:
        return len(self._request_handlers)


_default_bus: TypedEventBus | None = None


def get_default_event_bus(
    trace_sink: Callable[[dict[str, Any]], Coroutine[Any, Any, None]] | None = None,
) -> TypedEventBus:
    """Return the process-wide default plugin event bus."""
    global _default_bus
    if _default_bus is None:
        _default_bus = TypedEventBus(trace_sink=trace_sink)
    return _default_bus
