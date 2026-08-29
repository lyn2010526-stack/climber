"""Sliding window + automatic summarization.

Recent turns stay verbatim (default last 10). Every 5 new turns beyond the
window trigger a summary update: the summary model (lightweight call) takes
the old summary + the 5 turns about to leave the window and produces an
updated summary that keeps key facts, decisions, and unfinished items while
dropping small talk. The summary has a max length (4K tokens).
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class SlidingSummaryState:
    summary: str = ""
    last_summary_update: int = 0  # turn seq of last update


class SlidingWindowSummarizer:
    """Maintains a verbatim window plus a rolling summary.

    Args:
        window_size: turns kept verbatim (default 10).
        summary_step: new turns beyond the window that trigger an update
            (default 5).
        max_summary_chars: cap for the rolling summary.
        summarize_fn: optional async ``summarize(old_summary, turns) -> str``.
            When None, a simple extractive fallback is used.
    """

    def __init__(
        self,
        window_size: int = 10,
        summary_step: int = 5,
        max_summary_chars: int = 16000,  # ~4K tokens
        summarize_fn: Callable[..., Any] | None = None,
    ) -> None:
        self.window_size = window_size
        self.summary_step = summary_step
        self.max_summary_chars = max_summary_chars
        self._summarize_fn = summarize_fn
        self._state = SlidingSummaryState()
        self._turns: deque[dict[str, str]] = deque()
        self._evicted: deque[dict[str, str]] = deque()
        self._seq = 0

    def add_turn(self, role: str, content: str) -> bool:
        """Add a turn; returns True when a summary update is recommended."""
        self._seq += 1
        self._turns.append({"role": role, "content": content})
        triggered = False
        if len(self._turns) > self.window_size:
            self._evicted.append(self._turns.popleft())
            if len(self._evicted) >= self.summary_step:
                triggered = True
        return triggered

    def should_summarize(self) -> bool:
        return len(self._evicted) >= self.summary_step

    async def run_summary_update(self) -> str:
        """Consume the evicted batch and update the rolling summary."""
        if not self.should_summarize():
            return self._state.summary
        batch = list(self._evicted)
        self._evicted.clear()
        if self._summarize_fn is not None:
            try:
                result = await self._summarize_fn(self._state.summary, batch)
                if isinstance(result, str):
                    self._state.summary = result[: self.max_summary_chars]
                    self._state.last_summary_update = self._seq
                    return self._state.summary
            except Exception as exc:
                logger.warning("long_context.sliding_window.summarize_failed", error=str(exc))
        self._state.summary = self._extractive_fallback(
            self._state.summary, batch
        )[: self.max_summary_chars]
        self._state.last_summary_update = self._seq
        return self._state.summary

    def _extractive_fallback(self, old_summary: str, batch: list[dict[str, str]]) -> str:
        """Keep the old summary + key facts (first user lines) of the batch."""
        lines = []
        if old_summary:
            lines.append(old_summary)
        for turn in batch:
            if turn["role"] == "user":
                content = turn["content"].replace("\n", " ")[:200]
                if content:
                    lines.append(f"- {content}")
        return "\n".join(lines)

    def recent_turns(self) -> list[dict[str, str]]:
        return list(self._turns)

    def build_prompt_blocks(self) -> dict[str, str]:
        """Return {"summary": ..., "recent": ...} for prompt assembly."""
        recent = "\n".join(
            f"{t['role']}: {t['content']}" for t in self.recent_turns()
        )
        return {
            "summary": self._state.summary,
            "recent": recent,
        }
