"""Context compression for managing long conversations."""

from __future__ import annotations

import json
from typing import Any

import structlog

from app.core import CompressionStrategy, ContextConfig, MessageRole

logger = structlog.get_logger()

# Only these OpenAI-style fields are accepted by providers; anything else on
# a message dict is treated as internal bookkeeping and stripped before the
# message is sent back to the model.
_ALLOWED_MESSAGE_KEYS = ("role", "content", "tool_calls", "tool_call_id", "name")


def _strip_internal_fields(msg: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of msg keeping only provider-recognized fields."""
    return {k: msg[k] for k in _ALLOWED_MESSAGE_KEYS if k in msg}


def _drop_orphan_tool_prefix(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop leading tool results whose assistant tool_calls are absent.

    A role="tool" message is only valid when its paired assistant tool_calls
    message still appears earlier in the list. Cut points that land between
    a call and its result leave orphan tool results, which providers reject
    outright, so every truncation boundary must skip them.
    """
    start = 0
    while start < len(messages) and messages[start].get("role") == MessageRole.TOOL:
        start += 1
    return list(messages[start:])


def estimate_tokens(messages: list[dict[str, Any]]) -> int:
    """Rough token estimate: 1 token per 4 characters."""
    from app.core.context_aging import content_to_text

    total = 0
    for msg in messages:
        total += len(content_to_text(msg.get("content", ""))) // 4
        for tc in msg.get("tool_calls", []):
            total += len(str(tc)) // 4
    return total


class ContextCompressor:
    """Compresses conversation history when it exceeds token budget."""

    def __init__(self, config: ContextConfig):
        self._config = config

    def needs_compression(self, messages: list[dict[str, Any]]) -> bool:
        return estimate_tokens(messages) > self._config.max_tokens

    async def compress(self, messages: list[dict[str, Any]], model: Any) -> list[dict[str, Any]]:
        strategy = self._config.compression_strategy
        if strategy == CompressionStrategy.TRUNCATE:
            return self._truncate(messages)
        if strategy == CompressionStrategy.SLIDING:
            return self._sliding(messages)
        if strategy == CompressionStrategy.SUMMARIZE:
            return await self._summarize(messages, model)
        return messages

    def _truncate(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        keep = self._config.keep_recent_messages
        if len(messages) <= keep + 1:
            return messages
        result = messages[:1]
        result.append({"role": "system", "content": "[Earlier conversation truncated for brevity]"})
        result.extend(_drop_orphan_tool_prefix(messages[-(keep):]))
        return result

    def _sliding(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        keep = self._config.keep_recent_messages
        if len(messages) <= keep:
            return messages
        result = messages[:1]
        result.append({"role": "system", "content": "[Earlier messages truncated]"})
        result.extend(_drop_orphan_tool_prefix(messages[-(keep):]))
        return result

    async def _summarize(self, messages: list[dict[str, Any]], model: Any) -> list[dict[str, Any]]:
        """Summarize older messages into a single system message using the LLM.

        Keeps the first system prompt, summarizes the middle, retains the
        most recent `keep_recent_messages` verbatim for short-term recall.
        The summarization request reuses the live conversation prefix (session
        system prompt + original middle messages) so it hits the provider
        prefix cache. Falls back to truncation if the model call fails or the
        summary is not meaningfully shorter than the source.
        """
        keep = self._config.keep_recent_messages
        if len(messages) <= keep + 1:
            return messages

        head = messages[:1] if messages and messages[0].get("role") == MessageRole.SYSTEM else []
        tail = _drop_orphan_tool_prefix(messages[-keep:])
        middle = messages[len(head): -keep] if len(messages) > len(head) + keep else []
        if not middle:
            return messages

        turns = _group_into_turns(middle)
        manifest = _file_operation_manifest(middle)

        summary_instruction = (
            "Summarize the conversation above into a compact recap. Preserve key "
            "decisions, tool results, user requests, and any facts the assistant "
            "must remember. Label each turn as [turn N], numbering turns from 1 "
            "at each user message, so the summary stays addressable. Reply with "
            "a concise bullet list only."
        )
        # Reuse the session prefix verbatim instead of a detached two-message
        # prompt: the original conversation head and middle messages warm the
        # provider prefix cache. A middle ending on an assistant tool_calls
        # message is fine here — _message_text flattens the call info and the
        # summary may still mention it; only the output tail must stay
        # orphan-free, which _drop_orphan_tool_prefix guarantees.
        hold_messages = [_strip_internal_fields(m) for m in head]
        hold_messages.extend(_strip_internal_fields(m) for m in middle)
        hold_messages.append({"role": MessageRole.USER, "content": summary_instruction})

        try:
            # Reuse the adapter; treat adapter.chat as the async entry.
            result = await model.chat(messages=hold_messages, tools=None)
            summary_text = (result.content or "").strip() or "[Summary unavailable]"
        except Exception as e:
            logger.warning("summarize fallback to truncate", error=str(e))
            return self._truncate(messages)

        # Hard check: a recap that is not clearly shorter than the text it
        # replaces is pathological (e.g. the model echoed the transcript), and
        # truncation is the safer outcome in that case.
        original_len = sum(len(_message_text(m)) for m in middle)
        if original_len and len(summary_text) >= original_len * 0.9:
            logger.warning(
                "summary not shorter than source, fallback to truncate",
                summary_len=len(summary_text),
                original_len=original_len,
            )
            return self._truncate(messages)

        recap = f"[Summary of earlier conversation: turns {turns[0][0]}-{turns[-1][0]}]\n{summary_text}"
        if manifest:
            recap += "\n\n[Files touched in summarized turns]\n" + "\n".join(manifest)

        out = list(head)
        out.append({"role": MessageRole.SYSTEM, "content": recap})
        out.extend(tail)
        return out

    def compress_with_budget(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int,
        model: str = "gpt-4",
    ) -> list[dict[str, Any]]:
        """Compress messages to fit within token budget.

        Strategy:
        1. Keep all system messages
        2. Keep last N messages that fit in budget
        3. Summarize older messages
        """
        current_tokens = sum(estimate_tokens([m]) for m in messages)
        if current_tokens <= max_tokens:
            return messages

        system_msgs = [m for m in messages if m.get("role") == "system"]
        non_system = [m for m in messages if m.get("role") != "system"]

        system_tokens = sum(estimate_tokens([m]) for m in system_msgs)
        remaining_budget = max_tokens - system_tokens

        kept = []
        used_tokens = 0
        for msg in reversed(non_system):
            msg_tokens = estimate_tokens([msg])
            if used_tokens + msg_tokens <= remaining_budget * 0.8:
                kept.insert(0, msg)
                used_tokens += msg_tokens
            else:
                break

        # The budget cut can land between an assistant tool_calls message and
        # its tool result; drop any orphaned leading tool results.
        kept = _drop_orphan_tool_prefix(kept)

        summarized_count = len(non_system) - len(kept)
        if summarized_count > 0:
            summary = {
                "role": "system",
                "content": f"<summary of {summarized_count} earlier messages>",
            }
            return system_msgs + [summary] + kept

        return system_msgs + kept


def _message_text(msg: dict[str, Any]) -> str:
    """Flatten a message's content to text, including tool calls."""
    content = msg.get("content", "")
    if isinstance(content, list):
        parts = [b.get("text", "") for b in content if isinstance(b, dict)]
        text = " ".join(p for p in parts if p)
    else:
        text = content if isinstance(content, str) else str(content)
    for tc in msg.get("tool_calls", []) or []:
        function = tc.get("function", {}) if isinstance(tc, dict) else {}
        name = function.get("name", "")
        if name:
            text += f" [tool_call: {name}]"
    return text


def _group_into_turns(messages: list[dict[str, Any]]) -> list[tuple[int, list[dict[str, Any]]]]:
    """Group messages into turns starting at each user message.

    Messages before the first user message form turn 1 so nothing is dropped.
    """
    turns: list[tuple[int, list[dict[str, Any]]]] = []
    current: list[dict[str, Any]] = []
    turn_no = 1
    for msg in messages:
        if msg.get("role") == MessageRole.USER and current:
            turns.append((turn_no, current))
            turn_no += 1
            current = []
        current.append(msg)
    if current:
        turns.append((turn_no, current))
    return turns


def _file_operation_manifest(messages: list[dict[str, Any]]) -> list[str]:
    """Extract a deduplicated list of files referenced by tool calls."""
    seen: list[tuple[str, str]] = []
    for msg in messages:
        for tc in msg.get("tool_calls", []) or []:
            function = tc.get("function", {}) if isinstance(tc, dict) else {}
            name = function.get("name", "")
            if not name:
                continue
            raw = function.get("arguments", "{}")
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw)
                except json.JSONDecodeError:
                    continue
            if not isinstance(raw, dict):
                continue
            path = raw.get("path") or raw.get("file_path") or raw.get("filepath")
            if isinstance(path, str) and path and (name, path) not in seen:
                seen.append((name, path))
    return [f"- {name}: {path}" for name, path in seen]
