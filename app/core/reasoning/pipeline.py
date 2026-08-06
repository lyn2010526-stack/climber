"""ReasoningPipeline — unified entry point for multi-strategy reasoning.

Orchestrates strategy selection, execution, coverage checking, and result assembly.
Designed for progressive strategy activation (Phase 1: ToT, Phase 2: DeepRefine, Phase 3: Debate).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog

from app.core.reasoning.base import (
    ReasoningMode,
    ReasoningRequest,
    ReasoningResult,
)
from app.core.reasoning.components.coverage import CoverageChecker
from app.core.reasoning.components.scorer import CandidateScorer
from app.core.reasoning.components.self_refine import SelfRefineLoop
from app.core.reasoning.components.trace import ReasoningTracer
from app.core.reasoning.selector import StrategySelector

logger = structlog.get_logger()


class ReasoningPipeline:
    """Unified reasoning pipeline with pluggable strategies."""

    def __init__(
        self,
        model_registry: Any = None,
        cost_tracker: Any = None,
    ) -> None:
        self._strategies: dict[ReasoningMode, Any] = {}
        self._self_refine = SelfRefineLoop()
        self._coverage = CoverageChecker()
        self._scorer = CandidateScorer()
        self._selector = StrategySelector()
        self._tracer = ReasoningTracer()
        self._model_registry = model_registry
        self._cost_tracker = cost_tracker

    def register_strategy(self, mode: ReasoningMode, strategy: Any) -> None:
        """Register a reasoning strategy (progressive activation)."""
        self._strategies[mode] = strategy
        logger.info("strategy_registered", mode=mode.value, strategy=strategy.name)

    async def reason(self, request: ReasoningRequest) -> ReasoningResult:
        """Main entry point: execute reasoning and return result."""
        start = time.monotonic()
        self._tracer.start(request.task, request.mode)

        async def _run() -> ReasoningResult:
            mode = self._selector.select(request, self._strategies)
            strategy = self._strategies.get(mode)

            if strategy is None:
                logger.warning("strategy_not_registered", mode=mode.value, fallback="tree")
                mode = ReasoningMode.TREE_OF_THOUGHT
                strategy = self._strategies.get(mode)

            if strategy is None:
                raise NotImplementedError(f"No strategy registered for mode={mode.value}")

            logger.info("reasoning_start", mode=mode.value, strategy=strategy.name)

            candidates = await strategy.execute(request, self._self_refine, self._model_registry)

            if not candidates:
                return ReasoningResult(
                    answer="No valid candidates generated. Please try again.",
                    mode_used=mode,
                    total_duration_ms=(time.monotonic() - start) * 1000,
                )

            coverage = None
            if request.coverage_enabled:
                model_adapter = None
                if self._model_registry is not None:
                    try:
                        model_adapter = (
                            self._model_registry.get_or_create(request.model_override)
                            if request.model_override
                            else self._model_registry.get_default()
                        )
                    except Exception as exc:
                        logger.warning("coverage_model_resolve_failed", error=str(exc))

                coverage = await self._coverage.check(
                    task=request.task,
                    candidates=candidates,
                    model_adapter=model_adapter,
                    task_type=request.context.get("task_type", "general"),
                    timeout=request.timeout_seconds,
                )
                self._tracer.record_coverage(coverage)

            best = self._scorer.select_best(candidates, coverage)
            self._tracer.record_selection(
                f"Selected {best.id} (confidence={best.confidence:.2f}, path={best.path_type})"
            )

            trace = self._tracer.finish()
            elapsed = (time.monotonic() - start) * 1000

            logger.info(
                "reasoning_complete",
                mode=mode.value,
                candidates=len(candidates),
                best_id=best.id,
                best_confidence=best.confidence,
                coverage_score=coverage.score if coverage else None,
                duration_ms=round(elapsed, 1),
            )

            total_tokens = sum(
                getattr(c, 'token_usage', {}).get('total_tokens', 0) for c in candidates
            )
            total_cost = sum(
                getattr(c, 'estimated_cost', 0.0) for c in candidates
            )

            return ReasoningResult(
                answer=best.content,
                mode_used=mode,
                candidates=candidates,
                coverage=coverage,
                rounds=sum(c.round_created for c in candidates),
                total_duration_ms=round(elapsed, 1),
                trace=trace,
                total_tokens=total_tokens,
                estimated_cost=total_cost,
            )

        try:
            return await asyncio.wait_for(
                _run(),
                timeout=request.timeout_seconds,
            )
        except TimeoutError:
            elapsed = (time.monotonic() - start) * 1000
            logger.error(
                "reasoning_timeout", timeout=request.timeout_seconds, elapsed_ms=f"{elapsed:.0f}"
            )
            return ReasoningResult(
                answer=f"Reasoning timed out after {request.timeout_seconds}s. Please simplify the task or increase the timeout.",
                mode_used=request.mode,
                total_duration_ms=round(elapsed, 1),
            )
