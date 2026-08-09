"""Token usage tracker with quota protection.

Tracks token consumption across sessions and enforces limits
to prevent draining API balance.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TokenBudget:
    """Token budget configuration."""
    max_tokens_per_session: int = 100_000
    max_tokens_per_day: int = 1_000_000
    max_cost_per_day: float = 10.0  # USD
    warn_at_percent: float = 80.0  # Warn when 80% consumed


@dataclass
class TokenUsage:
    """Tracks token consumption."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    request_count: int = 0
    last_reset: float = field(default_factory=time.time)


class TokenTracker:
    """Track and limit token consumption."""

    # Approximate costs per token (USD)
    COST_PER_INPUT_TOKEN = 3.0 / 1_000_000   # Claude Sonnet pricing
    COST_PER_OUTPUT_TOKEN = 15.0 / 1_000_000

    def __init__(self, budget: TokenBudget | None = None):
        self.budget = budget or TokenBudget()
        self._sessions: dict[str, TokenUsage] = {}
        self._daily = TokenUsage()

    def record_usage(self, session_id: str, input_tokens: int, output_tokens: int):
        """Record token usage for a session."""
        if session_id not in self._sessions:
            self._sessions[session_id] = TokenUsage()

        sess = self._sessions[session_id]
        sess.input_tokens += input_tokens
        sess.output_tokens += output_tokens
        sess.total_tokens += input_tokens + output_tokens
        sess.request_count += 1
        sess.estimated_cost += input_tokens * self.COST_PER_INPUT_TOKEN
        sess.estimated_cost += output_tokens * self.COST_PER_OUTPUT_TOKEN

        self._daily.input_tokens += input_tokens
        self._daily.output_tokens += output_tokens
        self._daily.total_tokens += input_tokens + output_tokens
        self._daily.request_count += 1
        self._daily.estimated_cost = (
            self._daily.input_tokens * self.COST_PER_INPUT_TOKEN +
            self._daily.output_tokens * self.COST_PER_OUTPUT_TOKEN
        )

        self._check_limits(session_id)

    def _check_limits(self, session_id: str):
        """Check if any limits are exceeded."""
        sess = self._sessions[session_id]

        if sess.total_tokens >= self.budget.max_tokens_per_session:
            logger.error(
                "Session %s exceeded token limit: %d / %d",
                session_id, sess.total_tokens, self.budget.max_tokens_per_session,
            )
            raise QuotaExceededError(
                f"Session token limit reached: {sess.total_tokens}/{self.budget.max_tokens_per_session}"
            )

        if sess.total_tokens >= self.budget.max_tokens_per_session * self.budget.warn_at_percent / 100:
            logger.warning(
                "Session %s at %.0f%% of token budget (%d/%d)",
                session_id, self.budget.warn_at_percent,
                sess.total_tokens, self.budget.max_tokens_per_session,
            )

        if self._daily.estimated_cost >= self.budget.max_cost_per_day:
            logger.error(
                "Daily cost limit reached: $%.2f / $%.2f",
                self._daily.estimated_cost, self.budget.max_cost_per_day,
            )
            raise QuotaExceededError(
                f"Daily cost limit reached: ${self._daily.estimated_cost:.2f}/${self.budget.max_cost_per_day:.2f}"
            )

    def get_session_usage(self, session_id: str) -> TokenUsage:
        return self._sessions.get(session_id, TokenUsage())

    def get_daily_usage(self) -> TokenUsage:
        return self._daily

    def reset_daily(self):
        self._daily = TokenUsage()


class QuotaExceededError(Exception):
    """Raised when token/cost limit is exceeded."""
    pass
