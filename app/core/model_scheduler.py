"""Intelligent model scheduler with fallback chains.

Automatically selects the best model based on task complexity,
cost budget, and availability. Implements failover when a provider
is down or rate-limited.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum

from app.core.error_handler import CircuitBreaker

logger = logging.getLogger(__name__)


class TaskComplexity(str, Enum):
    SIMPLE = "simple"       # Single-step, factual
    MODERATE = "moderate"   # Multi-step reasoning
    COMPLEX = "complex"     # Deep analysis, multi-file
    CREATIVE = "creative"   # Open-ended generation


@dataclass
class ModelCapability:
    """Model capability profile."""
    provider: str           # "anthropic", "openai", "ollama"
    model_id: str
    max_context: int        # tokens
    supports_tools: bool
    supports_vision: bool
    cost_per_1k_input: float   # USD
    cost_per_1k_output: float  # USD
    speed_rating: float        # 1-10
    quality_rating: float      # 1-10
    priority: int = 0          # selection priority (lower = preferred)


@dataclass
class SchedulerConfig:
    """Model scheduler configuration."""
    default_provider: str = "anthropic"
    fallback_chain: list[str] = field(default_factory=lambda: [
        "anthropic/claude-sonnet-4-20250514",
        "openai/gpt-4o",
        "openai/gpt-4o-mini",
        "ollama/llama3.3",
    ])
    max_cost_per_task: float = 0.50  # USD
    prefer_local: bool = False
    quality_preference: float = 0.7  # 0=cost-first, 1=quality-first


class ModelScheduler:
    """Selects optimal model for each task."""

    def __init__(self, config: SchedulerConfig | None = None):
        self.config = config or SchedulerConfig()
        self._capabilities: dict[str, ModelCapability] = {}
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register known model capabilities."""
        defaults = [
            ModelCapability("anthropic", "claude-sonnet-4-20250514", 200000, True, True, 3.0, 15.0, 7, 9, 1),
            ModelCapability("anthropic", "claude-haiku-4-20250514", 200000, True, True, 0.25, 1.25, 9, 7, 2),
            ModelCapability("openai", "gpt-4o", 128000, True, True, 2.5, 10.0, 7, 8, 3),
            ModelCapability("openai", "gpt-4o-mini", 128000, True, True, 0.15, 0.6, 9, 7, 4),
            ModelCapability("ollama", "llama3.3", 8192, True, False, 0.0, 0.0, 5, 6, 5),
        ]
        for cap in defaults:
            key = f"{cap.provider}/{cap.model_id}"
            self._capabilities[key] = cap
            self._circuit_breakers[key] = CircuitBreaker(failure_threshold=3, recovery_timeout=120)

    def select_model(
        self,
        task_description: str,
        complexity: TaskComplexity = TaskComplexity.MODERATE,
        require_tools: bool = False,
        require_vision: bool = False,
        max_cost: float | None = None,
    ) -> str:
        """Select the best available model for a task.

        Returns: "provider/model_id" string
        """
        candidates = []

        for key, cap in self._capabilities.items():
            # Filter by requirements
            if require_tools and not cap.supports_tools:
                continue
            if require_vision and not cap.supports_vision:
                continue

            # Check circuit breaker
            cb = self._circuit_breakers[key]
            if cb.is_open:
                continue

            # Calculate score (higher = better)
            score = self._score_model(cap, complexity, max_cost)
            candidates.append((key, score, cap))

        if not candidates:
            logger.warning("No suitable model found, using fallback")
            return self.config.fallback_chain[0]

        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        selected = candidates[0][0]

        logger.info(
            "Selected model %s for %s task (score: %.2f)",
            selected, complexity.value, candidates[0][1],
        )
        return selected

    def _score_model(
        self,
        cap: ModelCapability,
        complexity: TaskComplexity,
        max_cost: float | None,
    ) -> float:
        """Score a model for a given task."""
        pref = self.config.quality_preference

        # Quality component (0-1)
        quality_score = cap.quality_rating / 10.0

        # Speed component (0-1)
        speed_score = cap.speed_rating / 10.0

        # Cost component (0-1, lower cost = higher score)
        max_input_cost = 10.0  # per 1k tokens
        cost_score = 1.0 - min(cap.cost_per_1k_input / max_input_cost, 1.0)

        # Complexity match
        complexity_bonus = 0.0
        if complexity == TaskComplexity.COMPLEX and cap.quality_rating >= 8:
            complexity_bonus = 0.2
        elif complexity == TaskComplexity.SIMPLE and cap.speed_rating >= 8:
            complexity_bonus = 0.1

        # Local preference
        local_bonus = 0.0
        if self.config.prefer_local and cap.provider == "ollama":
            local_bonus = 0.3

        score = (
            quality_score * pref +
            speed_score * (1 - pref) * 0.5 +
            cost_score * (1 - pref) * 0.5 +
            complexity_bonus +
            local_bonus
        )

        return score

    def record_success(self, provider_model: str):
        """Record a successful API call."""
        if provider_model in self._circuit_breakers:
            self._circuit_breakers[provider_model].record_success()

    def record_failure(self, provider_model: str):
        """Record a failed API call."""
        if provider_model in self._circuit_breakers:
            self._circuit_breakers[provider_model].record_failure()

    def get_fallback_chain(self, exclude: str | None = None) -> list[str]:
        """Get fallback chain excluding specified model."""
        chain = self.config.fallback_chain.copy()
        if exclude and exclude in chain:
            chain.remove(exclude)
        return chain
