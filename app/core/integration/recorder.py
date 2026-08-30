"""Runtime event recorder — single tap from the engine into the EventStore.

The recorder decouples the legacy engine from arch-v2: when no event store
is installed every call is a no-op, so the runtime works identically with
the master switch OFF. When the integration module is enabled, ``main.py``
installs the persistent store and all recorded events become durable.

Recording never breaks the main flow: store failures are logged and
swallowed, mirroring the ``_persist_message`` degradation pattern.
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()

# Lifecycle events worth persisting from the run loop. High-frequency TEXT
# deltas are excluded — message content is recorded via ``_persist_message``.
RECORDED_AGENT_EVENTS = frozenset(
    {
        "thinking",
        "tool_call",
        "tool_result",
        "checkpoint",
        "done",
        "error",
        "stopped",
        "context_compression",
    }
)

_store: Any = None


def set_event_store(store: Any) -> None:
    """Install the process-wide event store (None disables recording)."""
    global _store
    _store = store


def get_event_store() -> Any:
    return _store


def clear_event_store() -> None:
    global _store
    _store = None


async def record(session_id: str, event_type: str, data: dict[str, Any]) -> None:
    """Append one event to the installed store; no-op when disabled."""
    store = _store
    if store is None:
        return
    try:
        await store.append(event_type, data, stream_id=session_id)
    except Exception as exc:
        logger.warning(
            "event_recorder.append_failed",
            session_id=session_id,
            event_type=event_type,
            error=str(exc),
        )


def attach_session_recorder(session: Any) -> None:
    """Record every session state transition as a ``session_state`` event."""

    async def _hook(machine: Any, old: Any, new: Any) -> None:
        await record(
            machine.task_id,
            "session_state",
            {
                "from": old.value if hasattr(old, "value") else str(old),
                "to": new.value if hasattr(new, "value") else str(new),
            },
        )

    session.state_machine.add_hook(0, _hook)
