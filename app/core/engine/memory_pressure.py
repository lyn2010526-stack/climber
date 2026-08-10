"""Memory pressure management — reference: Letta context window management.

Features:
- Per-turn token usage detection
- Automatic compression when threshold exceeded
- Pressure alert deduplication (one alert per session until compression)
- Multiple compression strategies: summarize / drop tool results / keep system
- Manual + automatic dual-mode compression
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import structlog

logger = structlog.get_logger()


class CompressionStrategy(StrEnum):
    SUMMARIZE = "summarize"  # Summarize older messages
    DROP_TOOL_RESULTS = "drop_tool_results"  # Remove old tool outputs
    KEEP_SYSTEM = "keep_system"  # Only keep system + last N messages
    TRUNCATE = "truncate"  # Truncate long tool results


@dataclass
class MemoryPressureConfig:
    """Configuration for memory pressure management."""
    warning_threshold: float = 0.75  # Warn at 75% capacity
    critical_threshold: float = 0.90  # Force compress at 90%
    max_messages_keep: int = 20  # Max messages to keep after compression
    min_messages_keep: int = 4  # Minimum messages to always keep
    system_message_budget: int = 4000  # Tokens reserved for system prompt
    tool_result_max_tokens: int = 2000  # Truncate tool results beyond this
    compression_cooldown_turns: int = 2  # Min turns between compressions
    strategies: list[CompressionStrategy] = field(default_factory=lambda: [
        CompressionStrategy.TRUNCATE,
        CompressionStrategy.DROP_TOOL_RESULTS,
        CompressionStrategy.SUMMARIZE,
    ])


@dataclass
class PressureSnapshot:
    """Snapshot of current memory pressure state."""
    total_tokens: int
    max_tokens: int
    usage_ratio: float
    message_count: int
    tool_result_tokens: int
    system_tokens: int
    is_warning: bool
    is_critical: bool
    compression_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_tokens": self.total_tokens,
            "max_tokens": self.max_tokens,
            "usage_ratio": round(self.usage_ratio, 4),
            "message_count": self.message_count,
            "tool_result_tokens": self.tool_result_tokens,
            "system_tokens": self.system_tokens,
            "is_warning": self.is_warning,
            "is_critical": self.is_critical,
            "compression_count": self.compression_count,
        }


class MemoryPressureManager:
    """Manages context window memory pressure with automatic compression.

    Reference: Letta — proactive summarization when approaching context limits.
    """

    def __init__(self, config: MemoryPressureConfig | None = None) -> None:
        self._config = config or MemoryPressureConfig()
        self._compression_count = 0
        self._last_compression_turn = -100  # Force first turn can compress
        self._alerted_this_session = False

    def reset(self) -> None:
        """Reset session state."""
        self._compression_count = 0
        self._last_compression_turn = -100
        self._alerted_this_session = False

    def check_pressure(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int,
        *,
        current_turn: int = 0,
    ) -> PressureSnapshot:
        """Check current memory pressure.

        Args:
            messages: Current message list
            max_tokens: Maximum token limit for the model
            current_turn: Current turn number (for cooldown)

        Returns:
            PressureSnapshot with current state
        """
        total_tokens = self._estimate_tokens(messages)
        tool_result_tokens = self._count_tool_result_tokens(messages)
        system_tokens = self._count_system_tokens(messages)

        ratio = total_tokens / max_tokens if max_tokens > 0 else 0.0
        is_warning = ratio >= self._config.warning_threshold
        is_critical = ratio >= self._config.critical_threshold

        return PressureSnapshot(
            total_tokens=total_tokens,
            max_tokens=max_tokens,
            usage_ratio=ratio,
            message_count=len(messages),
            tool_result_tokens=tool_result_tokens,
            system_tokens=system_tokens,
            is_warning=is_warning,
            is_critical=is_critical,
            compression_count=self._compression_count,
        )

    def needs_compression(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int,
        *,
        current_turn: int = 0,
    ) -> bool:
        """Determine if compression is needed."""
        snapshot = self.check_pressure(messages, max_tokens, current_turn=current_turn)

        if not snapshot.is_critical and not snapshot.is_warning:
            return False

        # Critical always triggers; warning respects cooldown
        if snapshot.is_critical:
            return True

        # Warning-level: check cooldown
        turns_since_last = current_turn - self._last_compression_turn
        if turns_since_last < self._config.compression_cooldown_turns:
            return False

        return True

    def compress(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int,
        *,
        current_turn: int = 0,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Compress messages to reduce token usage.

        Returns:
            Tuple of (compressed_messages, compression_report)
        """
        import time
        start = time.monotonic()
        original_count = len(messages)
        original_tokens = self._estimate_tokens(messages)

        compressed = list(messages)
        strategies_applied: list[str] = []

        for strategy in self._config.strategies:
            if self._estimate_tokens(compressed) <= max_tokens * self._config.warning_threshold:
                break

            if strategy == CompressionStrategy.TRUNCATE:
                compressed = self._apply_truncate(compressed)
                strategies_applied.append("truncate")
            elif strategy == CompressionStrategy.DROP_TOOL_RESULTS:
                compressed = self._apply_drop_tool_results(compressed)
                strategies_applied.append("drop_tool_results")
            elif strategy == CompressionStrategy.KEEP_SYSTEM:
                compressed = self._apply_keep_system(compressed)
                strategies_applied.append("keep_system")
            elif strategy == CompressionStrategy.SUMMARIZE:
                compressed = self._apply_summarize(compressed)
                strategies_applied.append("summarize")

        self._compression_count += 1
        self._last_compression_turn = current_turn
        self._alerted_this_session = False

        new_tokens = self._estimate_tokens(compressed)
        duration = (time.monotonic() - start) * 1000

        report = {
            "strategies_applied": strategies_applied,
            "original_messages": original_count,
            "compressed_messages": len(compressed),
            "original_tokens": original_tokens,
            "compressed_tokens": new_tokens,
            "reduction_pct": round((1 - new_tokens / max(original_tokens, 1)) * 100, 2),
            "duration_ms": round(duration, 2),
            "compression_number": self._compression_count,
        }

        logger.info("memory_pressure.compressed", **report)
        return compressed, report

    def should_alert(self) -> bool:
        """Check if pressure alert should be shown (deduplication)."""
        if self._alerted_this_session:
            return False
        self._alerted_this_session = True
        return True

    @staticmethod
    def _estimate_tokens(messages: list[dict[str, Any]]) -> int:
        """Estimate token count from messages."""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += len(content) // 4  # Rough estimate: 1 token ≈ 4 chars
            tool_calls = msg.get("tool_calls", [])
            for tc in tool_calls:
                args = tc.get("function", {}).get("arguments", "")
                total += len(str(args)) // 4
        return total

    @staticmethod
    def _count_tool_result_tokens(messages: list[dict[str, Any]]) -> int:
        """Count tokens in tool result messages."""
        total = 0
        for msg in messages:
            if msg.get("role") == "tool":
                content = msg.get("content", "")
                total += len(str(content)) // 4
        return total

    @staticmethod
    def _count_system_tokens(messages: list[dict[str, Any]]) -> int:
        """Count tokens in system messages."""
        total = 0
        for msg in messages:
            if msg.get("role") == "system":
                total += len(str(msg.get("content", ""))) // 4
        return total

    def _apply_truncate(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Truncate long tool result messages."""
        max_tokens = self._config.tool_result_max_tokens
        result = []
        for msg in messages:
            if msg.get("role") == "tool":
                content = str(msg.get("content", ""))
                token_estimate = len(content) // 4
                if token_estimate > max_tokens:
                    # Truncate to max_tokens * 4 characters
                    truncated = content[:max_tokens * 4] + "\n... [truncated]"
                    msg = {**msg, "content": truncated}
            result.append(msg)
        return result

    def _apply_drop_tool_results(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Drop old tool results, keep only the most recent ones."""
        max_keep = self._config.max_messages_keep
        if len(messages) <= max_keep:
            return messages

        # Always keep system messages + last N messages
        system_msgs = [m for m in messages if m.get("role") == "system"]
        recent = messages[-(max_keep - len(system_msgs)):]
        return system_msgs + recent

    def _apply_keep_system(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Keep only system messages and last N messages."""
        system_msgs = [m for m in messages if m.get("role") == "system"]
        non_system = [m for m in messages if m.get("role") != "system"]
        keep_count = max(self._config.min_messages_keep - len(system_msgs), 2)
        return system_msgs + non_system[-keep_count:]

    def _apply_summarize(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Summarize older messages into a single context note."""
        if len(messages) <= self._config.min_messages_keep:
            return messages

        system_msgs = [m for m in messages if m.get("role") == "system"]
        non_system = [m for m in messages if m.get("role") != "system"]
        keep_count = self._config.min_messages_keep - len(system_msgs)

        # Keep recent messages, summarize older ones
        to_summarize = non_system[:-keep_count] if keep_count > 0 else non_system
        recent = non_system[-keep_count:] if keep_count > 0 else []

        if not to_summarize:
            return messages

        summary_parts = []
        for msg in to_summarize[:5]:  # Summarize up to 5 older messages
            role = msg.get("role", "unknown")
            content = str(msg.get("content", ""))[:100]
            summary_parts.append(f"{role}: {content}")

        summary_msg = {
            "role": "system",
            "content": f"[Previous context summary: {len(to_summarize)} earlier messages. Key points: {'; '.join(summary_parts)}]",
        }

        return [*system_msgs, summary_msg, *recent]
