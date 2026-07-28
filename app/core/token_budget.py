"""Token budget management.

"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TokenBudget:
    max_input_tokens: int = 8000
    max_output_tokens: int = 4096
    max_total_tokens: int = 12000
    reserved_system_tokens: int = 500
    warning_threshold: float = 0.8

    def remaining_input(self, used: int) -> int:
        return max(0, self.max_input_tokens - used)

    def remaining_output(self, used: int) -> int:
        return max(0, self.max_output_tokens - used)

    def is_over_budget(self, input_tokens: int, output_tokens: int) -> bool:
        return (input_tokens + output_tokens + self.reserved_system_tokens) > self.max_total_tokens

    def should_warn(self, input_tokens: int) -> bool:
        return input_tokens > self.max_input_tokens * self.warning_threshold


class Trimmer:
    """Trim long text to fit within token budget.

    """

    def __init__(self, max_chars: int = 30000):
        self.max_chars = max_chars

    def trim(self, text: str, max_chars: int | None = None) -> str:
        """Trim text to max_chars while preserving structure."""
        limit = max_chars or self.max_chars
        if len(text) <= limit:
            return text
        # Try to trim at a reasonable boundary
        trimmed = text[:limit]
        last_newline = trimmed.rfind("\n")
        if last_newline > limit * 0.8:
            trimmed = trimmed[:last_newline]
        return trimmed + "\n... [TRUNCATED]"

    def trim_messages(self, messages: list[dict[str, Any]], budget: TokenBudget) -> list[dict[str, Any]]:
        """Trim messages to fit within token budget."""
        from app.core.context_compressor import ContextCompressor, CompressionStrategy
        compressor = ContextCompressor(max_tokens=budget.max_input_tokens, system_tokens=budget.reserved_system_tokens)
        if compressor.needs_compression(messages):
            result = compressor.compress(messages, CompressionStrategy.SLIDING)
            return result.messages
        return messages


token_budget = TokenBudget()
trimmer = Trimmer()
