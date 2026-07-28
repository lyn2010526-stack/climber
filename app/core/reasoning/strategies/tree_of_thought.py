"""Tree-of-Thought reasoning strategy.

Implements multi-path parallel reasoning inspired by Princeton's ToT paper
(Yao et al., NeurIPS 2023) combined with Self-Refine vertical iteration.

Architecture:
- Horizontal: Generate N candidates in parallel, each from a different perspective
- Vertical: Each candidate undergoes Self-Refine critique-improve cycles
- Selection: Score all candidates, return the best one
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog

from app.core.reasoning.base import (
    Candidate,
    CritiqueResult,
    ReasoningRequest,
    RoundTrace,
)
from app.core.reasoning.components.scorer import CandidateScorer
from app.core.reasoning.components.self_refine import SelfRefineLoop
from app.core.reasoning.prompts.tree_prompts import (
    IMPROVE_PROMPT,
    PATH_SYSTEM_PROMPTS,
)

logger = structlog.get_logger()


class TreeOfThoughtStrategy:
    """Tree-of-Thought strategy: parallel multi-path + vertical self-refine."""

    name = "tree_of_thought"

    def __init__(self) -> None:
        self._scorer = CandidateScorer()

    async def execute(
        self,
        request: ReasoningRequest,
        self_refine: SelfRefineLoop,
        model_registry: Any,
    ) -> list[Candidate]:
        """Execute ToT reasoning: parallel paths → self-refine → return candidates."""
        model_adapter = self._get_model(request, model_registry)
        path_types = self._select_path_types(request.max_paths)

        concurrency_limit = min(request.max_paths, 5)
        semaphore = asyncio.Semaphore(concurrency_limit)

        async def _run_path_with_limit(idx: int, path_type: str) -> Candidate | None:
            async with semaphore:
                try:
                    return await self._run_path(request, path_type, self_refine, model_adapter, idx)
                except Exception as exc:
                    logger.error("tot_path_failed", path_type=path_type, error=str(exc))
                    return None

        start = time.monotonic()
        logger.info(
            "tot_start",
            task=request.task[:100],
            paths=request.max_paths,
            refine_rounds=request.max_refine_rounds,
            concurrency_limit=concurrency_limit,
        )

        tasks = [
            _run_path_with_limit(i, path_type)
            for i, path_type in enumerate(path_types)
        ]
        results = await asyncio.gather(*tasks)
        candidates = [r for r in results if r is not None]

        elapsed = (time.monotonic() - start) * 1000
        logger.info(
            "tot_complete",
            valid_paths=len(candidates),
            total_paths=request.max_paths,
            duration_ms=round(elapsed, 1),
        )
        return candidates

    async def _run_path(
        self,
        request: ReasoningRequest,
        path_type: str,
        self_refine: SelfRefineLoop,
        model_adapter: Any,
        path_index: int,
    ) -> Candidate:
        """Run a single reasoning path: generate → self-refine."""
        candidate_id = f"p{path_index}_{path_type[:3]}"
        path_start = time.monotonic()

        initial_content = await self._generate_initial(
            request.task, path_type, model_adapter, request.context
        )

        refined_content, critique, round_traces = await self._refine_path(
            request.task, initial_content, self_refine, model_adapter, path_type, request.max_refine_rounds
        )

        confidence = self._scorer.score_from_critique(critique)

        elapsed = (time.monotonic() - path_start) * 1000

        return Candidate(
            id=candidate_id,
            strategy=self.name,
            path_type=path_type,
            content=refined_content,
            reasoning_chain=[rt.output_summary for rt in round_traces],
            confidence=confidence,
            critique=critique,
            round_created=len(round_traces),
            duration_ms=round(elapsed, 1),
        )

    async def _generate_initial(
        self,
        task: str,
        path_type: str,
        model_adapter: Any,
        context: dict[str, Any],
    ) -> str:
        """Generate initial output from a specific perspective."""
        system_prompt = PATH_SYSTEM_PROMPTS.get(path_type, PATH_SYSTEM_PROMPTS["analytical"])
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task},
        ]

        parts: list[str] = []
        async for chunk in model_adapter.stream_chat(messages=messages):
            if chunk.content:
                parts.append(chunk.content)

        return "".join(parts)

    async def _refine_path(
        self,
        task: str,
        initial: str,
        self_refine: SelfRefineLoop,
        model_adapter: Any,
        path_type: str,
        max_rounds: int,
    ) -> tuple[str, CritiqueResult, list[RoundTrace]]:
        """Run self-refine loop on a single path."""
        return await self_refine.refine(
            task=task,
            initial=initial,
            model_adapter=model_adapter,
            path_type=path_type,
            max_rounds=max_rounds,
        )

    def _select_path_types(self, max_paths: int) -> list[str]:
        """Select diverse path types for parallel exploration."""
        all_types = ["analytical", "code_first", "research", "contrarian", "pragmatic"]
        return all_types[:max_paths]

    def _get_model(self, request: ReasoningRequest, model_registry: Any) -> Any:
        """Get model adapter from registry."""
        if request.model_override:
            return model_registry.get_or_create(request.model_override)
        return model_registry.get_default()
