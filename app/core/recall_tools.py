"""Session-scoped tools that retrieve archived tool outputs.

When context aging hides an old tool result it stashes the original text in a
per-session store keyed by ``tool_call_id`` and leaves a stub naming that id.
These tools close over that store so the model can pull the original back on
demand instead of losing it to truncation or pruning.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

_MAX_RECALL_CHARS = 30_000


def _clip(text: str) -> str:
    if len(text) <= _MAX_RECALL_CHARS:
        return text
    head = _MAX_RECALL_CHARS // 2
    tail = _MAX_RECALL_CHARS - head
    return f"{text[:head]}\n\n[recall clipped: {len(text)} chars total]\n\n{text[-tail:]}"


def recall_tool_definitions(
    store: dict[str, str],
) -> list[tuple[str, str, dict[str, Any], Callable]]:
    """Build recall tool specs bound to one session's hidden-output store."""

    def recall_tool_call(tool_call_id: str) -> str:
        text = store.get(tool_call_id)
        if text is None:
            known = ", ".join(sorted(store)) or "(none)"
            return f"No archived output for id '{tool_call_id}'. Available ids: {known}"
        return _clip(text)

    def recall_range(tool_call_id: str, start: int = 0, end: int = 0) -> str:
        text = store.get(tool_call_id)
        if text is None:
            known = ", ".join(sorted(store)) or "(none)"
            return f"No archived output for id '{tool_call_id}'. Available ids: {known}"
        if start < 0:
            start = 0
        if end <= start:
            end = min(len(text), start + _MAX_RECALL_CHARS)
        return _clip(text[start:end])

    call_schema = {
        "type": "object",
        "properties": {
            "tool_call_id": {
                "type": "string",
                "description": "The id shown in the recall stub for the hidden output.",
            }
        },
        "required": ["tool_call_id"],
    }
    range_schema = {
        "type": "object",
        "properties": {
            "tool_call_id": {
                "type": "string",
                "description": "The id shown in the recall stub for the hidden output.",
            },
            "start": {
                "type": "integer",
                "description": "Start character offset (default 0).",
            },
            "end": {
                "type": "integer",
                "description": "End character offset (default start + 30000).",
            },
        },
        "required": ["tool_call_id"],
    }

    return [
        (
            "recall_tool_call",
            "Retrieve the full text of a tool output hidden earlier by context aging.",
            call_schema,
            recall_tool_call,
        ),
        (
            "recall_range",
            "Retrieve a character range of a hidden tool output when it is too large to recall whole.",
            range_schema,
            recall_range,
        ),
    ]
