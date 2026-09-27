"""Tool-result truncation and history aging for context-cost control.

Two layers, both applied to the provider-facing message list so the
persisted transcript stays intact:

1. Write-time truncation (``truncate_tool_result``): caps a single tool
   result with middle-truncation (keep head + tail, drop the middle).
   The model keeps the command header and the final lines, which are the
   two regions it actually reasons over, while a multi-megabyte dump no
   longer fills the window.

2. History aging (``prune_old_tool_results``): before each LLM call,
   walks the tool results newest-to-oldest. Once the cumulative size
   exceeds a budget the oldest results are replaced with a short
   placeholder, and aging results in between are middle-truncated.

Both are pure functions over ``list[dict]`` and never mutate persistent
state; callers pass a copy when they need to keep the original.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Keep the head and tail of an oversized result; the middle is the least
# informative part of a log, diff, or directory listing.
TRUNCATION_MARKER = (
    "\n\n[Output truncated: showing first {head} + last {tail} of {total} "
    "characters ({elided} characters elided). To recover the missing part: "
    "re-run a more precise command (narrower grep pattern, head/tail/sed on "
    "a specific line range), or redirect full output to a file and search "
    "it there. Prefer commands that produce less output.]\n\n"
)

PRUNED_MARKER = (
    "[Tool output cleared - old result exceeded context budget. "
    "Re-run the tool if you need this information.]"
)

STUB_TEMPLATE = (
    "[Earlier tool output ({total} chars) hidden to save context. "
    "Use recall_tool_call(\"{tool_call_id}\") to retrieve the full text.]"
)

_TOOL_ROLES = {"tool", "toolResult"}


@dataclass(frozen=True)
class ToolResultConfig:
    """Budgets for the two truncation layers.

    ``max_result_chars=0`` disables write-time truncation;
    ``prune_budget_chars=0`` disables history aging.
    """

    max_result_chars: int = 30_000
    head_ratio: float = 0.4
    tail_ratio: float = 0.4
    prune_protect_recent: int = 6
    prune_budget_chars: int = 80_000
    disclose_budget_chars: int = 120_000


def truncate_tool_result(text: str, config: ToolResultConfig | None = None) -> str:
    """Middle-truncate ``text`` when it exceeds the configured limit."""
    cfg = config or ToolResultConfig()
    max_chars = cfg.max_result_chars
    if max_chars <= 0 or len(text) <= max_chars:
        return text

    head_chars = max(1, int(max_chars * cfg.head_ratio))
    tail_chars = max(1, int(max_chars * cfg.tail_ratio))
    elided = max(0, len(text) - head_chars - tail_chars)
    marker = TRUNCATION_MARKER.format(
        head=head_chars, tail=tail_chars, total=len(text), elided=elided
    )
    return text[:head_chars] + marker + text[-tail_chars:]


def _content_text_length(content: Any) -> int:
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        total = 0
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                total += len(block["text"])
        return total
    return 0


def _rewrite_content(content: Any, transform: Any) -> Any:
    """Apply ``transform`` to every text block, preserving structure.

    Non-text blocks (images, tool-call metadata) are passed through so a
    multimodal message survives aging without losing its attachments.
    """
    if isinstance(content, str):
        return transform(content)
    if isinstance(content, list):
        rewritten = []
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                block = {**block, "text": transform(block["text"])}
            rewritten.append(block)
        return rewritten
    return content


def make_stub(tool_call_id: str, total_chars: int) -> str:
    """Build the placeholder that replaces a hidden tool result."""
    return STUB_TEMPLATE.format(tool_call_id=tool_call_id, total=total_chars)


def disclose_old_tool_results(
    messages: list[dict[str, Any]],
    store: dict[str, str],
    config: ToolResultConfig | None = None,
) -> int:
    """Replace aged tool results with recall stubs, archiving originals.

    Unlike :func:`prune_old_tool_results` (which drops content), this keeps
    the original text recoverable: the full output is written into ``store``
    keyed by the message's ``tool_call_id`` and the transcript is replaced
    with a short stub naming that id. The model can call ``recall_tool_call``
    to pull the original back on demand.

    Returns the number of results stubbed.
    """
    cfg = config or ToolResultConfig()
    budget = cfg.disclose_budget_chars
    if budget <= 0:
        return 0

    entries: list[tuple[int, str, int]] = []
    for index, msg in enumerate(messages):
        if msg.get("role") not in _TOOL_ROLES:
            continue
        length = _content_text_length(msg.get("content"))
        if length <= 0:
            continue
        key = msg.get("tool_call_id") or f"msg-{index}"
        entries.append((index, key, length))
    if not entries:
        return 0

    protect_recent = max(0, cfg.prune_protect_recent)
    cumulative = 0
    boundary: int | None = None
    for position in range(len(entries) - 1, -1, -1):
        _index, _key, length = entries[position]
        cumulative += length
        reverse_pos = len(entries) - 1 - position
        if reverse_pos < protect_recent:
            continue
        if cumulative > budget:
            boundary = position
            break
    if boundary is None:
        return 0

    stubbed = 0
    for position in range(0, boundary + 1):
        index, key, length = entries[position]
        original = _content_to_text(messages[index].get("content"))
        store.setdefault(key, original)
        stub = make_stub(key, length)
        messages[index]["content"] = _rewrite_content(
            messages[index].get("content"), lambda _text: stub
        )
        stubbed += 1
    return stubbed


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and isinstance(block.get("text"), str)
        )
    return str(content)


# Public alias: safe text extraction for any message content shape
# (plain string or multimodal block list).
content_to_text = _content_to_text


def prune_old_tool_results(
    messages: list[dict[str, Any]],
    config: ToolResultConfig | None = None,
) -> int:
    """Age old tool results in place; return the number rewritten.

    The most recent ``prune_protect_recent`` results are left untouched.
    Beyond the cumulative budget the oldest results become placeholders;
    between the budget boundary and the protected zone, oversized results
    are middle-truncated rather than dropped, so the model still sees
    their shape.
    """
    cfg = config or ToolResultConfig()
    budget = cfg.prune_budget_chars
    if budget <= 0:
        return 0

    entries: list[tuple[int, int]] = []
    for index, msg in enumerate(messages):
        if msg.get("role") not in _TOOL_ROLES:
            continue
        length = _content_text_length(msg.get("content"))
        if length > 0:
            entries.append((index, length))
    if not entries:
        return 0

    protect_recent = max(0, cfg.prune_protect_recent)
    prune_from: int | None = None
    truncate_from: int | None = None
    cumulative = 0
    for position in range(len(entries) - 1, -1, -1):
        _index, length = entries[position]
        cumulative += length
        reverse_pos = len(entries) - 1 - position
        if reverse_pos < protect_recent:
            continue
        if prune_from is None and cumulative > budget:
            prune_from = position
            break
        if truncate_from is None:
            truncate_from = position

    rewritten = 0

    if prune_from is not None:
        for position in range(0, prune_from + 1):
            index, _ = entries[position]
            messages[index]["content"] = _rewrite_content(
                messages[index].get("content"), lambda _text: PRUNED_MARKER
            )
            rewritten += 1

    if cfg.max_result_chars > 0:
        start = prune_from + 1 if prune_from is not None else 0
        end = truncate_from if truncate_from is not None else -1
        for position in range(start, end + 1):
            index, length = entries[position]
            if length <= cfg.max_result_chars:
                continue
            messages[index]["content"] = _rewrite_content(
                messages[index].get("content"),
                lambda text: truncate_tool_result(text, cfg),
            )
            rewritten += 1

    return rewritten
