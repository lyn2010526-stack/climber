"""Event-stream projections.

Pure reducers over the persistent event stream: every view of the runtime
(session state, trajectory, statistics, skill usage) is derived from events
rather than maintained as separate mutable state, so any projection can be
rebuilt at any time and audited against the append-only log.
"""

from __future__ import annotations

from typing import Any

from app.core.integration.event_store import EventStore

#: Event types that form the agent execution timeline.
TRAJECTORY_EVENT_TYPES = (
    "thinking",
    "tool_call",
    "tool_result",
    "checkpoint",
    "done",
    "error",
    "stopped",
    "context_compression",
)


async def project_session(store: EventStore, session_id: str) -> dict[str, Any]:
    """Rebuild the current state of one session from its event stream."""
    status: str | None = None
    message_count = 0
    tool_calls = 0
    iterations = 0

    for event in await store.read(stream_id=session_id, limit=1_000_000):
        etype, data = event["event_type"], event["data"]
        if etype == "session_state":
            status = data.get("to", status)
        elif etype == "message":
            message_count += 1
        elif etype == "tool_call":
            tool_calls += 1
        elif etype == "thinking":
            iterations = max(iterations, int(data.get("iteration", 0)))

    return {
        "session_id": session_id,
        "status": status,
        "message_count": message_count,
        "tool_calls": tool_calls,
        "iterations": iterations,
    }


async def project_trajectory(store: EventStore, session_id: str) -> list[dict[str, Any]]:
    """Return the ordered execution timeline of one session."""
    events = await store.read(stream_id=session_id, limit=1_000_000)
    return [e for e in events if e["event_type"] in TRAJECTORY_EVENT_TYPES]


async def project_stats(store: EventStore, session_id: str | None = None) -> dict[str, Any]:
    """Aggregate message/tool/token statistics over the event stream."""
    messages = 0
    tool_calls_total = 0
    tool_calls_by_name: dict[str, int] = {}
    tokens = 0

    for event in await store.read(stream_id=session_id, limit=1_000_000):
        etype, data = event["event_type"], event["data"]
        if etype == "message":
            messages += 1
        elif etype == "tool_call":
            tool_calls_total += 1
            name = data.get("name") or "unknown"
            tool_calls_by_name[name] = tool_calls_by_name.get(name, 0) + 1
        elif etype == "done":
            tokens += int(data.get("tokens_used", 0))

    return {
        "messages": messages,
        "tool_calls_total": tool_calls_total,
        "tool_calls_by_name": tool_calls_by_name,
        "tokens": tokens,
    }


async def project_skill_usage(store: EventStore, session_id: str | None = None) -> dict[str, int]:
    """Count skill loads per skill id."""
    usage: dict[str, int] = {}
    for event in await store.read(
        stream_id=session_id, event_type="skill_load", limit=1_000_000
    ):
        skill_id = event["data"].get("skill_id") or "unknown"
        usage[skill_id] = usage.get(skill_id, 0) + 1
    return usage
