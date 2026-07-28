"""Context compression for managing long conversations."""

from __future__ import annotations

import json
from typing import Any

import structlog

from app.core import ChatResult, CompressionStrategy, ContextConfig, MessageRole

logger = structlog.get_logger()


def estimate_tokens(messages: list[dict[str, Any]]) -> int:
    """Rough token estimate: 1 token per 4 characters."""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        total += len(content) // 4
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
        result.extend(messages[-(keep):])
        return result

    def _sliding(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        keep = self._config.keep_recent_messages
        if len(messages) <= keep:
            return messages
        return messages[-keep:]

    async def _summarize(self, messages: list[dict[str, Any]], model: Any) -> list[dict[str, Any]]:
        """Summarize older messages into a single system message using the LLM.

        Keeps the first system prompt, summarizes the middle, retains the
        most recent `keep_recent_messages` verbatim for short-term recall.
        Falls back to truncation if the model call fails.
        """
        keep = self._config.keep_recent_messages
        if len(messages) <= keep + 1:
            return messages

        head = messages[:1] if messages and messages[0].get("role") == MessageRole.SYSTEM else []
        tail = messages[-keep:]
        middle = messages[len(head): -keep] if len(messages) > len(head) + keep else []
        if not middle:
            return messages

        summary_prompt = (
            "Summarize the following conversation turns into a compact recap. "
            "Preserve key decisions, tool results, user requests, and any facts the "
            "assistant must remember. Reply with a concise bullet list only.\n\n"
        )
        try:
            for msg in middle:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                summary_prompt += f"[{role}] {content[:1000]}\n"

            hold_messages = [
                {"role": MessageRole.SYSTEM, "content": "You are a conversation summarizer."},
                {"role": MessageRole.USER, "content": summary_prompt},
            ]
            # Reuse the adapter; treat adapter.chat as the async entry.
            result = await model.chat(messages=hold_messages, tools=None)
            summary_text = (result.content or "").strip() or "[Summary unavailable]"
        except Exception as e:
            logger.warning("summarize fallback to truncate", error=str(e))
            return self._truncate(messages)

        out = list(head)
        out.append({
            "role": MessageRole.SYSTEM,
            "content": f"[Summary of earlier conversation]\n{summary_text}",
        })
        out.extend(tail)
        return out
