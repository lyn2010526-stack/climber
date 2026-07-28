"""Context compression strategies.

"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CompressionStrategy(Enum):
    TRUNCATE = "truncate"
    SLIDING = "sliding"
    SUMMARIZE = "summarize"


@dataclass
class CompressionResult:
    strategy: CompressionStrategy
    original_tokens: int
    compressed_tokens: int
    messages: list[dict[str, Any]]
    summary: str | None = None


class ContextCompressor:
    """Compress context when approaching token budget.

    """

    def __init__(self, max_tokens: int = 8000, system_tokens: int = 500):
        self.max_tokens = max_tokens
        self.system_tokens = system_tokens
        self._threshold = 0.8

    def estimate_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Estimate token count (roughly 1 token per 4 chars)."""
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        return total_chars // 4

    def needs_compression(self, messages: list[dict[str, Any]]) -> bool:
        return self.estimate_tokens(messages) > self.max_tokens * self._threshold

    def compress(self, messages: list[dict[str, Any]], strategy: CompressionStrategy = CompressionStrategy.SUMMARIZE) -> CompressionResult:
        original_tokens = self.estimate_tokens(messages)
        if original_tokens <= self.max_tokens:
            return CompressionResult(
                strategy=CompressionStrategy.TRUNCATE,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                messages=messages,
            )

        system_messages = [m for m in messages if m.get("role") == "system"]
        non_system = [m for m in messages if m.get("role") != "system"]

        if strategy == CompressionStrategy.TRUNCATE:
            # Keep system + last N messages
            keep_count = max(1, (self.max_tokens - self.system_tokens) // 200)
            compressed = system_messages + non_system[-keep_count:]
            return CompressionResult(
                strategy=CompressionStrategy.TRUNCATE,
                original_tokens=original_tokens,
                compressed_tokens=self.estimate_tokens(compressed),
                messages=compressed,
            )

        elif strategy == CompressionStrategy.SLIDING:
            # Keep system + last N messages within budget
            available = self.max_tokens - self.system_tokens
            kept = []
            total = 0
            for msg in reversed(non_system):
                msg_tokens = len(str(msg.get("content", ""))) // 4
                if total + msg_tokens > available:
                    break
                kept.insert(0, msg)
                total += msg_tokens
            compressed = system_messages + kept
            return CompressionResult(
                strategy=CompressionStrategy.SLIDING,
                original_tokens=original_tokens,
                compressed_tokens=self.estimate_tokens(compressed),
                messages=compressed,
            )

        else:  # SUMMARIZE
            # TODO: Implement LLM-based summarization
            # For now, fallback to SLIDING
            return self.compress(messages, CompressionStrategy.SLIDING)


context_compressor = ContextCompressor()
