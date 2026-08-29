"""Smart context compression middleware.

Enhances context management with:
- Importance scoring for messages
- Tool result compression (large outputs summarized)
- Priority-based retention
- Proactive compression before hitting limits
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from app.core.middleware import MiddlewareBase

if TYPE_CHECKING:
    from app.core.agent_engine import AgentEngine, AgentSession

logger = structlog.get_logger()


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: 1 token per 4 characters."""
    return len(text) // 4


def _score_message_importance(msg: dict[str, Any]) -> float:
    """Score message importance (0.0 to 1.0).

    Higher scores = more important to keep.
    """
    role = msg.get("role", "")
    content = str(msg.get("content", ""))
    score = 0.5  # base score

    # System messages are always important
    if role == "system":
        score = 0.9

    # User messages are important (they contain intent)
    elif role == "user":
        score = 0.8
        # Longer user messages are more important
        if len(content) > 200:
            score = 0.85

    # Assistant messages with tool calls are important
    elif role == "assistant":
        if msg.get("tool_calls"):
            score = 0.7
        else:
            score = 0.6

    # Tool results: compress large ones
    elif role == "tool":
        tokens = _estimate_tokens(content)
        if tokens > 500:
            score = 0.3  # large tool output, less important
        elif tokens > 100:
            score = 0.5
        else:
            score = 0.6

    # Messages with errors are important (need to avoid repeating)
    if "error" in content.lower():
        score = max(score, 0.75)

    # Messages with decisions/conclusions are important
    if any(kw in content.lower() for kw in ["decision:", "conclusion:", "result:", "summary:"]):
        score = max(score, 0.8)

    return min(score, 1.0)


def _compress_tool_result(content: str, max_tokens: int = 200) -> str:
    """Compress a large tool result to fit within token budget."""
    tokens = _estimate_tokens(content)
    if tokens <= max_tokens:
        return content

    # Keep first and last portions
    chars = max_tokens * 4
    half = chars // 2
    if len(content) <= chars:
        return content

    return (
        content[:half]
        + f"\n... [truncated, {tokens} tokens total] ...\n"
        + content[-half:]
    )


class SmartCompressionMiddleware(MiddlewareBase):
    """Middleware that provides intelligent context compression.

    Features:
    - Scores message importance and retains high-value messages
    - Compresses large tool results automatically
    - Applies proactive compression before hitting limits
    - Maintains conversation coherence during compression
    """

    def __init__(
        self,
        importance_threshold: float = 0.4,
        tool_result_max_tokens: int = 200,
        proactive_ratio: float = 0.75,
    ):
        self.importance_threshold = importance_threshold
        self.tool_result_max_tokens = tool_result_max_tokens
        self.proactive_ratio = proactive_ratio

    async def on_compress_context(
        self,
        engine: AgentEngine,
        session: AgentSession,
        input_kwargs: dict[str, Any],
        next_handler: Any,
    ) -> None:
        """Smart compression: compress tool results first, then compress by importance."""
        messages = session.messages

        # Step 1: Compress large tool results in-place
        compressed_count = 0
        for msg in messages:
            if msg.get("role") == "tool":
                content = msg.get("content", "")
                if _estimate_tokens(content) > self.tool_result_max_tokens:
                    msg["content"] = _compress_tool_result(content, self.tool_result_max_tokens)
                    compressed_count += 1

        if compressed_count > 0:
            logger.info(
                "smart_compression.compressed_tool_results",
                count=compressed_count,
            )

        # Step 2: If still over budget, compress by importance
        from app.core.compressor import estimate_tokens
        current_tokens = estimate_tokens(messages)
        max_tokens = input_kwargs.get("ctx_limit", 8000)

        if current_tokens > max_tokens * self.proactive_ratio:
            # Score and sort messages by importance
            scored = [
                (i, _score_message_importance(msg))
                for i, msg in enumerate(messages)
            ]

            # Keep system messages and high-importance messages
            system_indices = {
                i for i, msg in enumerate(messages)
                if msg.get("role") == "system"
            }

            # Remove low-importance messages (but keep system and recent)
            to_remove = []
            for i, score in scored:
                if (
                    i not in system_indices
                    and score < self.importance_threshold
                    and i < len(messages) - 3  # keep last 3 messages
                ):
                    to_remove.append(i)

            if to_remove:
                for i in sorted(to_remove, reverse=True):
                    messages.pop(i)
                logger.info(
                    "smart_compression.removed_low_importance",
                    count=len(to_remove),
                )

        # Delegate to original compression if still needed
        await next_handler()
