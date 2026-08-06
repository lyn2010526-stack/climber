"""Router decision system — reference: OpenSquilla RouterDecision.

Produces structured routing events for every model selection decision.
Supports C0-C3 tiered routing, confidence scoring, and decision audit logging.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class RouterDecisionEvent:
    """Structured record of a single routing decision."""
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: float = field(default_factory=time.monotonic)
    target_tier: str = "C1"
    model: str = ""
    provider: str = ""
    confidence: float = 0.0
    probabilities: dict[str, float] = field(default_factory=dict)
    savings_pct: float = 0.0
    fallback_reason: str | None = None
    route_source: str = "classifier"
    latency_ms: float = 0.0
    task_complexity: float = 0.5  # 0-1 scale

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "target_tier": self.target_tier,
            "model": self.model,
            "provider": self.provider,
            "confidence": round(self.confidence, 4),
            "probabilities": {k: round(v, 4) for k, v in self.probabilities.items()},
            "savings_pct": round(self.savings_pct, 2),
            "fallback_reason": self.fallback_reason,
            "route_source": self.route_source,
            "latency_ms": round(self.latency_ms, 2),
            "task_complexity": round(self.task_complexity, 3),
        }


@dataclass
class TierConfig:
    """Configuration for a routing tier."""
    name: str
    models: list[tuple[str, str]]  # (provider, model_id) pairs
    max_tokens: int = 4096
    cost_per_1k: float = 0.01
    capability_score: float = 0.5  # 0-1, higher = more capable


class RouterDecisionEngine:
    """Makes structured routing decisions based on task complexity and model health.

    Tier model (reference: OpenSquilla router_tiers):
    - C0: Ultra-lightweight — simple greetings, confirmations
    - C1: Standard — most conversational tasks
    - C2: Enhanced — multi-step reasoning, tool use
    - C3: Premium — complex planning, code generation, analysis
    """

    def __init__(self, tiers: dict[str, TierConfig] | None = None):
        self._tiers: dict[str, TierConfig] = tiers or self._default_tiers()
        self._decision_log: list[RouterDecisionEvent] = []
        self._max_log_size = 1000

    @staticmethod
    def _default_tiers() -> dict[str, TierConfig]:
        return {
            "C0": TierConfig(
                name="ultra_light",
                models=[("openai", "gpt-4o-mini")],
                max_tokens=2048,
                cost_per_1k=0.001,
                capability_score=0.3,
            ),
            "C1": TierConfig(
                name="standard",
                models=[("openai", "gpt-4o")],
                max_tokens=4096,
                cost_per_1k=0.01,
                capability_score=0.6,
            ),
            "C2": TierConfig(
                name="enhanced",
                models=[("openai", "gpt-4o"), ("anthropic", "claude-sonnet-4-20250514")],
                max_tokens=8192,
                cost_per_1k=0.03,
                capability_score=0.8,
            ),
            "C3": TierConfig(
                name="premium",
                models=[("anthropic", "claude-opus-4-20250514")],
                max_tokens=16384,
                cost_per_1k=0.10,
                capability_score=1.0,
            ),
        }

    def estimate_complexity(self, message: str, *, tool_count: int = 0, history_len: int = 0) -> float:
        """Estimate task complexity on a 0-1 scale.

        Heuristic based on message length, tool requirements, and conversation depth.
        """
        score = 0.0

        # Length factor (longer messages tend to be more complex)
        msg_len = len(message)
        if msg_len < 50:
            score += 0.1
        elif msg_len < 200:
            score += 0.2
        elif msg_len < 1000:
            score += 0.3
        else:
            score += 0.4

        # Tool usage factor
        if tool_count > 5:
            score += 0.3
        elif tool_count > 2:
            score += 0.2
        elif tool_count > 0:
            score += 0.1

        # Conversation depth factor
        if history_len > 10:
            score += 0.2
        elif history_len > 5:
            score += 0.1

        # Keyword-based boost
        complex_keywords = ["analyze", "plan", "architecture", "implement", "refactor", "debug", "optimize", "design"]
        if any(kw in message.lower() for kw in complex_keywords):
            score += 0.15

        return min(score, 1.0)

    def select_tier(self, complexity: float) -> str:
        """Select routing tier based on complexity score.

        Clamps to the highest available tier if custom tiers don't include C3.
        """
        available = sorted(self._tiers.keys())
        if not available:
            return "C1"

        if complexity < 0.2:
            target = "C0"
        elif complexity < 0.45:
            target = "C1"
        elif complexity < 0.7:
            target = "C2"
        else:
            target = "C3"

        # If target tier doesn't exist, clamp to nearest available
        if target not in self._tiers:
            # Find highest available tier <= target
            tier_order = ["C0", "C1", "C2", "C3"]
            target_idx = tier_order.index(target)
            for i in range(target_idx, -1, -1):
                if tier_order[i] in self._tiers:
                    return tier_order[i]
            return available[0]  # Fallback to lowest available

        return target

    def decide(
        self,
        message: str,
        *,
        available_models: list[tuple[str, str]] | None = None,
        tool_count: int = 0,
        history_len: int = 0,
        user_override: str | None = None,
        previous_tier: str | None = None,
    ) -> RouterDecisionEvent:
        """Make a routing decision and log it.

        Args:
            message: User message
            available_models: List of (provider, model_id) pairs that are available
            tool_count: Number of tools available
            history_len: Number of previous messages
            user_override: Force a specific tier (user override)
            previous_tier: Previous tier (for fallback decisions)

        Returns:
            RouterDecisionEvent with full decision details
        """
        start = time.monotonic()

        complexity = self.estimate_complexity(message, tool_count=tool_count, history_len=history_len)

        if user_override and user_override in self._tiers:
            tier_name = user_override
            route_source = "user_override"
            confidence = 1.0
        else:
            tier_name = self.select_tier(complexity)
            route_source = "classifier"
            # Confidence is higher at tier boundaries
            confidence = 0.7 + 0.3 * abs(complexity - 0.5)

        tier = self._tiers[tier_name]

        # Select model from tier
        if available_models:
            # Find first available model in tier
            model_match = None
            for tm in tier.models:
                if tm in available_models:
                    model_match = tm
                    break
            if model_match:
                provider, model_id = model_match
            else:
                provider, model_id = tier.models[0]
                route_source = "fallback"
        else:
            provider, model_id = tier.models[0]

        # Calculate savings vs most expensive tier
        max_cost = max(t.cost_per_1k for t in self._tiers.values()) if self._tiers else 0
        savings = ((max_cost - tier.cost_per_1k) / max_cost * 100) if max_cost > 0 else 0

        # Build probability distribution
        probabilities = {}
        for t_name, _t_config in self._tiers.items():
            if t_name == tier_name:
                probabilities[t_name] = confidence
            else:
                probabilities[t_name] = (1 - confidence) / max(len(self._tiers) - 1, 1)

        latency = (time.monotonic() - start) * 1000

        event = RouterDecisionEvent(
            target_tier=tier_name,
            model=model_id,
            provider=provider,
            confidence=confidence,
            probabilities=probabilities,
            savings_pct=savings,
            fallback_reason=f"fallback from {previous_tier}" if previous_tier and previous_tier != tier_name else None,
            route_source=route_source,
            latency_ms=latency,
            task_complexity=complexity,
        )

        self._log_decision(event)
        return event

    def _log_decision(self, event: RouterDecisionEvent) -> None:
        """Append decision to log, with size cap."""
        self._decision_log.append(event)
        if len(self._decision_log) > self._max_log_size:
            self._decision_log = self._decision_log[-self._max_log_size // 2:]

    def get_decision_log(self, last_n: int = 50) -> list[RouterDecisionEvent]:
        """Get recent decisions for audit/debugging."""
        return self._decision_log[-last_n:]

    def get_stats(self) -> dict[str, Any]:
        """Get routing statistics."""
        if not self._decision_log:
            return {"total_decisions": 0}

        tier_counts: dict[str, int] = {}
        source_counts: dict[str, int] = {}
        total_savings = 0.0
        total_confidence = 0.0

        for d in self._decision_log:
            tier_counts[d.target_tier] = tier_counts.get(d.target_tier, 0) + 1
            source_counts[d.route_source] = source_counts.get(d.route_source, 0) + 1
            total_savings += d.savings_pct
            total_confidence += d.confidence

        n = len(self._decision_log)
        return {
            "total_decisions": n,
            "tier_distribution": tier_counts,
            "source_distribution": source_counts,
            "avg_confidence": round(total_confidence / n, 4),
            "avg_savings_pct": round(total_savings / n, 2),
        }
