"""Reasoning service facade wired into AgentEngine.

Exposes `is_available()` and a `.pipeline` attribute consumed by
app/core/reasoning/api.py. Registers the available strategies (ToT, deep_refine,
debate) on construction so the chain is actually live.
"""

from __future__ import annotations

from typing import Any

import structlog

from app.core.reasoning.base import ReasoningMode
from app.core.reasoning.pipeline import ReasoningPipeline

logger = structlog.get_logger()


class ReasoningService:
    def __init__(self, model_registry: Any = None, cost_tracker: Any = None) -> None:
        self.pipeline = ReasoningPipeline(model_registry=model_registry, cost_tracker=cost_tracker)
        try:
            from app.core.reasoning.strategies.tree_of_thought import TreeOfThoughtStrategy

            self.pipeline.register_strategy(ReasoningMode.TREE_OF_THOUGHT, TreeOfThoughtStrategy())
        except Exception as exc:  # pragma: no cover - defensive import
            logger.warning("reasoning_strategy_registration_failed", strategy="tree_of_thought", error=str(exc))
        try:
            from app.core.reasoning.strategies.deep_refine import DeepRefineStrategy

            self.pipeline.register_strategy(ReasoningMode.DEEP_REFINE, DeepRefineStrategy())
        except Exception as exc:  # pragma: no cover
            logger.warning("reasoning_strategy_registration_failed", strategy="deep_refine", error=str(exc))
        try:
            from app.core.reasoning.strategies.debate import DebateStrategy

            self.pipeline.register_strategy(ReasoningMode.DEBATE, DebateStrategy())
        except Exception as exc:  # pragma: no cover
            logger.warning("reasoning_strategy_registration_failed", strategy="debate", error=str(exc))

    def is_available(self) -> bool:
        return self.pipeline is not None and bool(self.pipeline._strategies)
