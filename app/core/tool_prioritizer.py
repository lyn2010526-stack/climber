"""Tool prioritization with lightweight learning.

"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger()


def _tokenize(text: str) -> set[str]:
    """Lowercase word tokens for lightweight semantic matching."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two token sets."""
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass
class ToolStats:
    """Cumulative stats for a single tool."""

    attempts: int = 0
    successes: int = 0
    total_duration_ms: float = 0.0
    description_length: int = 0


class ToolPrioritizer:
    """Rank available tools by relevance to the current task.

    Scoring formula (reference: Suna tool auto-priority):
        relevance_score = semantic_similarity(task, tool_desc)
        success_rate     = historical_success / total_attempts
        cost_score       = 1 / (1 + avg_token_cost)
        final_score      = 0.5 * relevance + 0.3 * success_rate + 0.2 * cost_score
    """

    def __init__(self) -> None:
        self._stats: dict[str, ToolStats] = defaultdict(ToolStats)
        self._description_cache: dict[str, str] = {}

    def rank_tools(self, task_description: str, tools: list[dict[str, Any]]) -> list[str]:
        """Return tool names sorted by descending priority."""
        scored: list[tuple[float, str]] = []
        tokens = _tokenize(task_description)
        for tool in tools:
            name = tool.get("function", {}).get("name") or tool.get("name", "")
            desc = tool.get("function", {}).get("description") or tool.get("description", "")
            if not name:
                continue
            self._description_cache[name] = desc
            stats = self._stats[name]
            if desc:
                stats.description_length = max(stats.description_length, len(desc))
            relevance = _jaccard(tokens, _tokenize(desc))
            if stats.attempts == 0:
                success_rate = 0.5
                avg_cost = max(stats.description_length / 4.0, 1.0)
            else:
                success_rate = stats.successes / stats.attempts
                avg_cost = max(stats.total_duration_ms / stats.attempts / 100.0, 0.1)
            cost_score = 1.0 / (1.0 + avg_cost)
            final_score = 0.5 * relevance + 0.3 * success_rate + 0.2 * cost_score
            scored.append((final_score, name))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [name for _, name in scored]

    def record_outcome(self, tool_name: str, success: bool, duration_ms: float, tokens: int = 0) -> None:
        """Update stats after a tool execution."""
        stats = self._stats[tool_name]
        stats.attempts += 1
        if success:
            stats.successes += 1
        stats.total_duration_ms += duration_ms
        logger.debug("tool_prioritizer.record_outcome", tool=tool_name, success=success, duration_ms=duration_ms)

    def get_stats(self, tool_name: str) -> dict[str, Any]:
        """Return learned stats for a tool."""
        stats = self._stats.get(tool_name, ToolStats())
        if stats.attempts > 0:
            return {
                "attempts": stats.attempts,
                "success_rate": stats.successes / stats.attempts,
                "avg_duration_ms": stats.total_duration_ms / stats.attempts,
            }
        return {"attempts": 0, "success_rate": None, "avg_duration_ms": None}
