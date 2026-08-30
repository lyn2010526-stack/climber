"""Wire the self-learning loop into the live event stream.

- L1 (RealtimeFixer) subscribes to ``tool_result`` events: when a tool whose
  name matches a stored skill fails, the skill's instruction is patched.
- L2 (BackgroundDistiller) subscribes to ``session_complete``: the session's
  tool-call trajectory is pulled from the persistent event store and
  distilled into a reusable skill in a background task.

Both subscriptions degrade silently when their event source is missing, so
the wiring is safe with any subset of arch-v2 switches enabled.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from app.core.self_learning.l2_distill import OperationRecord

logger = structlog.get_logger()

#: Background tasks kept alive until completion (fire-and-forget guard).
_background_tasks: set[asyncio.Task] = set()


def wire_self_learning(
    l1: Any,
    l2: Any,
    skill_store: Any,
    bus: Any,
    event_store: Any = None,
) -> None:
    """Subscribe L1/L2 to their trigger events on the legacy event bus."""

    async def _on_tool_result(event: dict[str, Any]) -> None:
        error = event.get("error") or ""
        if not error:
            return
        tool_name = event.get("tool_name") or ""
        skill = skill_store.get(tool_name)
        if skill is None:
            return
        try:
            fixed, _new = l1.fix(tool_name, error, skill.load_instruction())
            if fixed:
                logger.info("self_learning.l1_applied", skill_id=tool_name)
        except Exception as exc:
            logger.warning("self_learning.l1_failed", skill_id=tool_name, error=str(exc))

    async def _on_session_complete(event: dict[str, Any]) -> None:
        session_id = event.get("session_id") or ""
        if not session_id or event_store is None:
            return
        try:
            tool_calls = await event_store.read(stream_id=session_id, event_type="tool_call")
            messages = await event_store.read(stream_id=session_id, event_type="message")
        except Exception as exc:
            logger.warning("self_learning.l2_read_failed", session_id=session_id, error=str(exc))
            return
        operations = [
            OperationRecord(operation=str(call["data"].get("name", "unknown")))
            for call in tool_calls
        ]
        title = next(
            (
                str(m["data"].get("content", ""))[:80]
                for m in messages
                if m["data"].get("role") == "user" and m["data"].get("content")
            ),
            f"session:{session_id}",
        )
        task = asyncio.create_task(l2.distill(title, operations))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    bus.subscribe("tool_result", _on_tool_result)
    bus.subscribe("session_complete", _on_session_complete)
    logger.info("self_learning.wired")
