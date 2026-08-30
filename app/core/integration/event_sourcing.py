"""Event sourcing state layer.

All state is a projection of an append-only event stream:
- the current conversation is the projection of all message events
- the skill library is the projection of skill create/update events
- statistics are aggregation projections over the event stream
- the UI is a live projection of relevant events

Benefit: time travel (rebuild any historical state), full audit trail, and
state reconstruction by replaying the event stream after loss.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EventSourcedStore:
    """An append-only event log with projection functions.

    Args:
        apply: async ``apply(state, event) -> state`` reducer used to rebuild
            a projection from the stream.
        initial_state: state used before any event is applied.
    """

    name: str
    apply: Callable[..., Any]
    initial_state: Any = None
    events: list[dict[str, Any]] = field(default_factory=list)

    async def project(self, upto: int | None = None) -> Any:
        """Replay the stream to rebuild current (or historical) state."""
        state = self.initial_state
        target = upto if upto is not None else len(self.events)
        for event in self.events[:target]:
            state = await self.apply(state, event)
        return state


class EventSourcingManager:
    """Manages multiple event-sourced stores sharing one event stream.

    Args:
        event_store: optional persistent append-only store. When set, every
            emitted event is persisted and :meth:`restore` rebuilds the
            in-memory stream from disk after a restart.
        stream_id: stream used when persisting to ``event_store``.
    """

    def __init__(self, event_store: Any = None, stream_id: str = "main") -> None:
        self._stores: dict[str, EventSourcedStore] = {}
        self._events: list[dict[str, Any]] = []
        self._stream_id: str = stream_id
        self._event_store = event_store

    def register_store(self, store: EventSourcedStore) -> None:
        store.events = self._events
        self._stores[store.name] = store

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        if self._event_store is not None:
            await self._event_store.append(event_type, data, stream_id=self._stream_id)
        self._events.append({"type": event_type, **data})
        # Rebuild affected projections lazily by name; callers can also
        # query any store's project().
        for store in self._stores.values():
            # touch the store so the shared list is used on next project()
            store.events = self._events

    async def restore(self) -> int:
        """Reload the shared stream from the persistent event store.

        Returns the number of events loaded. No-op without an event store.
        """
        if self._event_store is None:
            return 0
        persisted = await self._event_store.read(stream_id=self._stream_id)
        self._events.clear()
        for event in persisted:
            self._events.append({"type": event["event_type"], **event["data"]})
        for store in self._stores.values():
            store.events = self._events
        return len(self._events)

    def get_store(self, name: str) -> EventSourcedStore | None:
        return self._stores.get(name)

    async def snapshot(self) -> dict[str, Any]:
        """Return projections of every registered store (time-travel view)."""
        result: dict[str, Any] = {}
        for name, store in self._stores.items():
            result[name] = await store.project()
        return result

    def event_count(self) -> int:
        return len(self._events)

    def stream(self) -> list[dict[str, Any]]:
        return list(self._events)


_default_es: EventSourcingManager | None = None


def get_event_sourcing_manager() -> EventSourcingManager:
    global _default_es
    if _default_es is None:
        _default_es = EventSourcingManager()
    return _default_es
