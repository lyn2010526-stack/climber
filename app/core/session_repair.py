"""Session history repair: guarantee tool-call/result pairing.

Inspired by deepseek-harness's session repair. If a run is interrupted
mid-execution (crash, timeout, cancellation), the transcript can contain
assistant messages with tool_calls that never received a result. Most
providers reject such histories outright, so a recovered session would be
permanently broken. This module synthesizes explicit error results for
unanswered calls so the history is valid and the model knows the tool
outcome is unknown.
"""

from __future__ import annotations

from typing import Any

INTERRUPTED_RESULT = (
    "[Tool execution was interrupted before completing. "
    "The tool may or may not have run. "
    "Re-run it if you need its result.]"
)


def repair_unpaired_tool_calls(
    messages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Insert synthetic error results for unanswered tool calls.

    Args:
        messages: Provider-style message list (dicts with role/content/
            tool_calls/tool_call_id).

    Returns:
        (repaired_messages, inserted_count). The input list is not mutated;
        when nothing is missing the original list is returned unchanged.
    """
    answered: set[str] = set()
    for msg in messages:
        if msg.get("role") == "tool":
            call_id = msg.get("tool_call_id")
            if call_id:
                answered.add(call_id)

    repaired: list[dict[str, Any]] = []
    inserted = 0
    for msg in messages:
        repaired.append(msg)
        if msg.get("role") != "assistant":
            continue
        tool_calls = msg.get("tool_calls") or []
        missing = [
            tc.get("id")
            for tc in tool_calls
            if tc.get("id") and tc["id"] not in answered
        ]
        for call_id in missing:
            repaired.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": INTERRUPTED_RESULT,
            })
            answered.add(call_id)
            inserted += 1

    if not inserted:
        return messages, 0
    return repaired, inserted
