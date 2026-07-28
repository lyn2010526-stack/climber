"""Tool performance monitoring.

"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ToolCallStats:
    tool_name: str
    total_calls: int = 0
    success_calls: int = 0
    failed_calls: int = 0
    total_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    min_duration_ms: float = float("inf")
    last_error: str | None = None
    recent_durations: list[float] = field(default_factory=list)


class ToolPerformanceMonitor:
    """Monitor tool execution performance.

    """

    def __init__(self, max_samples: int = 100):
        self._stats: dict[str, ToolCallStats] = {}
        self._max_samples = max_samples

    def record(self, tool_name: str, duration_ms: float, success: bool, error: str | None = None) -> None:
        stats = self._stats.setdefault(tool_name, ToolCallStats(tool_name=tool_name))
        stats.total_calls += 1
        stats.total_duration_ms += duration_ms
        stats.max_duration_ms = max(stats.max_duration_ms, duration_ms)
        stats.min_duration_ms = min(stats.min_duration_ms, duration_ms)
        stats.recent_durations.append(duration_ms)
        if len(stats.recent_durations) > self._max_samples:
            stats.recent_durations = stats.recent_durations[-self._max_samples:]
        if success:
            stats.success_calls += 1
        else:
            stats.failed_calls += 1
            stats.last_error = error

    def get_stats(self, tool_name: str) -> dict[str, Any] | None:
        stats = self._stats.get(tool_name)
        if not stats:
            return None
        return {
            "tool_name": stats.tool_name,
            "total_calls": stats.total_calls,
            "success_calls": stats.success_calls,
            "failed_calls": stats.failed_calls,
            "success_rate": stats.success_calls / stats.total_calls if stats.total_calls > 0 else 0.0,
            "avg_duration_ms": stats.total_duration_ms / stats.total_calls if stats.total_calls > 0 else 0.0,
            "max_duration_ms": stats.max_duration_ms,
            "min_duration_ms": stats.min_duration_ms if stats.min_duration_ms != float("inf") else 0.0,
            "last_error": stats.last_error,
        }

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        return {name: self.get_stats(name) for name in self._stats}

    def get_slow_tools(self, threshold_ms: float = 1000.0) -> list[dict[str, Any]]:
        slow = []
        for name, stats in self._stats.items():
            avg = stats.total_duration_ms / stats.total_calls if stats.total_calls > 0 else 0.0
            if avg > threshold_ms:
                slow.append(self.get_stats(name))
        return slow


tool_performance_monitor = ToolPerformanceMonitor()
