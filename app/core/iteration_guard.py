"""Iteration guard for multi-agent loops.

Prevents:
- Infinite iteration loops
- Stagnation (no progress over N rounds)
- Deadlock (agents stuck in opposition)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class IterationMetrics:
    """Track iteration health."""
    round_count: int = 0
    score_history: list[float] = field(default_factory=list)
    last_improvement_round: int = 0
    stagnation_rounds: int = 0
    start_time: float = field(default_factory=time.monotonic)

    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.start_time


@dataclass
class GuardConfig:
    max_rounds: int = 20
    max_stagnation_rounds: int = 5
    max_duration_seconds: float = 1800.0  # 30 minutes
    min_improvement_threshold: float = 0.01  # 1%


class IterationGuard:
    """Guard against infinite loops and stagnation in multi-agent loops."""

    def __init__(self, config: GuardConfig | None = None):
        self.config = config or GuardConfig()
        self._sessions: dict[str, IterationMetrics] = {}

    def start_session(self, session_id: str):
        self._sessions[session_id] = IterationMetrics()

    def record_round(self, session_id: str, score: float | None = None) -> dict:
        """Record an iteration round. Returns status dict."""
        metrics = self._sessions.setdefault(session_id, IterationMetrics())
        metrics.round_count += 1

        if score is not None:
            metrics.score_history.append(score)

            if len(metrics.score_history) >= 2:
                improvement = metrics.score_history[-1] - metrics.score_history[-2]
                if improvement >= self.config.min_improvement_threshold:
                    metrics.last_improvement_round = metrics.round_count
                    metrics.stagnation_rounds = 0
                else:
                    metrics.stagnation_rounds += 1
            else:
                metrics.last_improvement_round = metrics.round_count

        return self.check_status(session_id)

    def check_status(self, session_id: str) -> dict:
        """Check if iteration should continue."""
        metrics = self._sessions.get(session_id)
        if not metrics:
            return {"continue": True, "reason": ""}

        if metrics.round_count >= self.config.max_rounds:
            return {
                "continue": False,
                "reason": f"Max rounds ({self.config.max_rounds}) reached",
                "metrics": {"rounds": metrics.round_count},
            }

        if metrics.elapsed_seconds >= self.config.max_duration_seconds:
            return {
                "continue": False,
                "reason": f"Max duration ({self.config.max_duration_seconds}s) reached",
                "metrics": {"elapsed": metrics.elapsed_seconds},
            }

        if metrics.stagnation_rounds >= self.config.max_stagnation_rounds:
            return {
                "continue": False,
                "reason": f"Stagnation detected: {metrics.stagnation_rounds} rounds without improvement",
                "metrics": {"stagnation_rounds": metrics.stagnation_rounds},
            }

        return {
            "continue": True,
            "reason": "",
            "metrics": {
                "rounds": metrics.round_count,
                "elapsed": metrics.elapsed_seconds,
                "stagnation": metrics.stagnation_rounds,
            },
        }

    def get_metrics(self, session_id: str) -> IterationMetrics | None:
        return self._sessions.get(session_id)
