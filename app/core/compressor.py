"""Context compression for managing long conversations.

Design references:
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- https://docs.letta.com/v1-sdk/concepts/stateful-agents
- https://langchain-ai.github.io/langmem/concepts/conceptual_guide/
"""

from __future__ import annotations

from typing import Any

import structlog

from app.core import CompressionStrategy, ContextConfig, MessageRole

logger = structlog.get_logger()


def estimate_tokens(messages: list[dict[str, Any]]) -> int:
    """Rough token estimate: 1 token per 4 characters."""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        total += len(str(content)) // 4
        for tc in msg.get("tool_calls", []):
            total += len(str(tc)) // 4
    return total


class ContextCompressor:
    """Compresses conversation history when it exceeds token budget."""

    def __init__(self, config: ContextConfig):
        self._config = config

    def needs_compression(self, messages: list[dict[str, Any]]) -> bool:
        threshold = self._config.max_tokens * self._config.summarize_threshold
        return estimate_tokens(messages) >= threshold

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
        if keep < 1 or len(messages) <= keep:
            return messages
        head = self._system_messages(messages)
        result = list(head)
        result.append({"role": "system", "content": "[Earlier conversation truncated for brevity]"})
        result.extend(self._keep_complete_turns(messages, keep))
        return result

    def _sliding(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        keep = self._config.keep_recent_messages
        if keep < 1 or len(messages) <= keep:
            return messages
        head = self._system_messages(messages)
        result = list(head)
        result.append({"role": "system", "content": "[Earlier messages truncated]"})
        result.extend(self._keep_complete_turns(messages, keep))
        return result

    @staticmethod
    def _system_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Keep every system instruction; system messages are pinned context."""
        return [message for message in messages if message.get("role") == MessageRole.SYSTEM]

    @staticmethod
    def _keep_complete_turns(messages: list[dict[str, Any]], keep: int) -> list[dict[str, Any]]:
        """Keep the most recent `keep` complete turns without splitting an
        assistant message's tool_calls from its following TOOL result messages.

        A turn is a non-TOOL message plus any immediately following TOOL
        messages. Walking backwards from the tail, the first turn whose tool
        results are cut off is extended to include its leading non-TOOL message
        so the assistant/tool pairing survives compression intact.
        """
        non_system = [message for message in messages if message.get("role") != MessageRole.SYSTEM]
        if keep >= len(non_system):
            return non_system
        tail = non_system[-keep:]
        rest = non_system[:-keep]
        if tail and tail[0].get("role") == MessageRole.TOOL and rest:
            return rest[-1:] + tail
        if (
            tail
            and tail[0].get("role") == MessageRole.ASSISTANT
            and tail[0].get("tool_calls")
            and len(rest) >= 2
            and rest[-1].get("role") == MessageRole.TOOL
        ):
            return rest[-2:] + tail
        return tail

    async def _summarize(self, messages: list[dict[str, Any]], model: Any) -> list[dict[str, Any]]:
        """Summarize older messages into a single system message using the LLM.

        Keeps the first system prompt, summarizes the middle, retains the
        most recent `keep_recent_messages` verbatim for short-term recall.
        Falls back to truncation if the model call fails.
        """
        keep = self._config.keep_recent_messages
        if keep < 1 or len(messages) <= keep:
            return messages

        head = self._system_messages(messages)
        non_system = [message for message in messages if message.get("role") != MessageRole.SYSTEM]
        tail = self._keep_complete_turns(non_system, keep)
        middle = non_system[: -len(tail)] if tail else non_system
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
                content = str(msg.get("content", ""))
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

    def compress_with_budget(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int,
        _model: str = "gpt-4",
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

        system_msgs = self._system_messages(messages)
        non_system = [m for m in messages if m.get("role") != "system"]

        system_tokens = sum(estimate_tokens([m]) for m in system_msgs)
        remaining_budget = max_tokens - system_tokens

        kept: list[dict[str, Any]] = []
        used_tokens = 0
        for msg in reversed(non_system):
            msg_tokens = estimate_tokens([msg])
            if used_tokens + msg_tokens <= max(0, remaining_budget):
                kept.insert(0, msg)
                used_tokens += msg_tokens
            else:
                break

        kept = self._keep_complete_turns(kept, len(kept)) if kept else kept

        summarized_count = len(non_system) - len(kept)
        if summarized_count > 0:
            summary = {
                "role": "system",
                "content": (
                    f"[Earlier context omitted: {summarized_count} messages. "
                    "Use conversation search or memory tools when exact details are needed.]"
                ),
            }
            return [*system_msgs, summary, *kept]

        return system_msgs + kept
