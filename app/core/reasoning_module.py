"""ReasoningModule — isolated reasoning engine component.

Extracted from AgentEngine to follow single-responsibility principle.
Encapsulates pipeline initialization, strategy registration, and cost tracking.
"""

from __future__ import annotations

from typing import Any

import structlog

from app.core.reasoning.base import ReasoningMode
from app.core.reasoning.pipeline import ReasoningPipeline
from app.core.reasoning.strategies.tree_of_thought import TreeOfThoughtStrategy
from app.core.reasoning.strategies.deep_refine import DeepRefineStrategy
from app.core.reasoning.strategies.debate import DebateStrategy

logger = structlog.get_logger()


class ReasoningModule:
    """Isolated reasoning engine with pluggable strategies.

    Responsibilities:
    - Initialize ReasoningPipeline with all registered strategies
    - Inject dependencies (cost_tracker, model_registry)
    - Expose pipeline for reasoning requests
    """

    def __init__(self, cost_tracker: Any = None) -> None:
        self._cost_tracker = cost_tracker
        self._pipeline = self._build_pipeline()

    def _build_pipeline(self) -> ReasoningPipeline | None:
        """Build and register all reasoning strategies."""
        try:
            pipeline = ReasoningPipeline(cost_tracker=self._cost_tracker)
            pipeline.register_strategy(
                ReasoningMode.TREE_OF_THOUGHT,
                TreeOfThoughtStrategy(),
            )
            pipeline.register_strategy(
                ReasoningMode.DEEP_REFINE,
                DeepRefineStrategy(),
            )
            pipeline.register_strategy(
                ReasoningMode.DEBATE,
                DebateStrategy(),
            )
            logger.info("reasoning_module_initialized", strategies=3)
            return pipeline
        except Exception as exc:
            logger.error("reasoning_module_init_failed", error=str(exc))
            return None

    @property
    def pipeline(self) -> ReasoningPipeline | None:
        """Return the underlying ReasoningPipeline instance."""
        return self._pipeline

    def is_available(self) -> bool:
        """Check if reasoning engine is ready."""
        return self._pipeline is not None

    def __repr__(self) -> str:
        status = "ready" if self._pipeline else "unavailable"
        return f"ReasoningModule(status={status}, cost_tracker={self._cost_tracker is not None})"
