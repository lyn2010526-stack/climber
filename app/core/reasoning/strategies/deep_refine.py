"""DeepRefineStrategy — Reflexion-style iterative refinement with backtracking.

Implements vertical-depth reasoning with persistent reflection memory,
per-round snapshots, and backtracking when stuck in local optima.


Architecture:
- Generate initial solution
- Critique → Reflect (on failure) → Improve (with lessons)
- Snapshot after each round for potential backtracking
- Backtrack if stuck (no improvement for N rounds)
- Return best solution found across all attempts
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import structlog
from pydantic import ValidationError

from app.core.reasoning.base import (
    Candidate,
    CritiqueResult,
    ReasoningRequest,
    RoundTrace,
)
from app.core.reasoning.components.coverage import CoverageChecker
from app.core.reasoning.components.reflection_memory import ReflectionMemory
from app.core.reasoning.components.scorer import CandidateScorer
from app.core.reasoning.components.self_refine import SelfRefineLoop, _parse_critique_response
from app.core.reasoning.prompts.deep_refine_prompts import (
    BACKTRACK_DECISION_PROMPT,
    DEEP_REFINE_SYSTEM_PROMPT,
    REFLECTION_GENERATION_PROMPT,
)

logger = structlog.get_logger()

_CRITIQUE_SCHEMA = {
    "type": "object",
    "required": ["passed", "issues", "scores"],
    "properties": {
        "passed": {"type": "boolean"},
        "summary": {"type": "string"},
        "scores": {
            "type": "object",
            "properties": {
                "correctness": {"type": "number", "minimum": 1, "maximum": 5},
                "completeness": {"type": "number", "minimum": 1, "maximum": 5},
                "clarity": {"type": "number", "minimum": 1, "maximum": 5},
                "safety": {"type": "number", "minimum": 1, "maximum": 5},
                "actionability": {"type": "number", "minimum": 1, "maximum": 5},
            },
        },
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["severity", "description"],
                "properties": {
                    "severity": {"type": "string", "enum": ["critical", "major", "minor", "info"]},
                    "description": {"type": "string"},
                    "location": {"type": "string"},
                    "fix_suggestion": {"type": "string"},
                },
            },
        },
    },
}

_REFLECTION_SCHEMA = {
    "type": "object",
    "required": ["failure_reason", "lesson", "suggested_approach"],
    "properties": {
        "failure_reason": {"type": "string"},
        "lesson": {"type": "string"},
        "suggested_approach": {"type": "string"},
    },
}


class Snapshot:
    """Per-round snapshot for backtracking."""

    def __init__(self, content: str, confidence: float, round_num: int, summary: str = "") -> None:
        self.content = content
        self.confidence = confidence
        self.round_num = round_num
        self.summary = summary
        self.timestamp = time.monotonic()


class DeepRefineStrategy:
    """DeepRefine strategy: iterative refinement with reflection memory and backtracking."""

    name = "deep_refine"

    def __init__(self) -> None:
        self._scorer = CandidateScorer()

    async def execute(
        self,
        request: ReasoningRequest,
        self_refine: SelfRefineLoop,
        model_registry: Any,
    ) -> list[Candidate]:
        """Execute deep refinement: generate → critique → reflect → improve → backtrack if stuck."""
        model_adapter = self._get_model(request, model_registry)
        reflection_memory = ReflectionMemory()
        snapshots: list[Snapshot] = []

        start = time.monotonic()
        logger.info(
            "deep_refine_start",
            task=request.task[:100],
            max_rounds=request.max_refine_rounds,
        )

        initial_content = await self._generate_initial(request.task, model_adapter, request.context)
        snapshots.append(Snapshot(initial_content, 0.5, 0, "Initial generation"))

        current = initial_content
        best_content = current
        best_confidence = 0.5
        best_critique: CritiqueResult | None = None
        all_traces: list[RoundTrace] = []
        consecutive_no_improvement = 0

        for round_num in range(1, request.max_refine_rounds + 1):
            round_start = time.monotonic()

            critique = await self._run_critique(request.task, current, model_adapter, round_num, request.max_refine_rounds)
            confidence = self._scorer.score_from_critique(critique)
            duration = (time.monotonic() - round_start) * 1000

            all_traces.append(RoundTrace(
                round_num=round_num,
                action="critique",
                input_summary=request.task[:100],
                output_summary=f"passed={critique.passed}, avg={critique.average_score:.2f}, confidence={confidence:.2f}",
                duration_ms=duration,
            ))

            if confidence > best_confidence:
                best_confidence = confidence
                best_content = current
                best_critique = critique
                consecutive_no_improvement = 0
            else:
                consecutive_no_improvement += 1

            if self._should_stop(critique):
                logger.info("deep_refine_converged", round=round_num, confidence=confidence)
                break

            if round_num == request.max_refine_rounds:
                break

            if consecutive_no_improvement >= 2:
                backtrack_decision = await self._decide_backtrack(
                    current, critique.average_score, reflection_memory.size,
                    round_num, model_adapter,
                )
                if backtrack_decision == "backtrack" and snapshots:
                    snapshot = max(snapshots, key=lambda s: s.confidence)
                    if snapshot.confidence > confidence:
                        logger.info("deep_refine_backtracking", to_round=snapshot.round_num)
                        current = snapshot.content
                        all_traces.append(RoundTrace(
                            round_num=round_num,
                            action="backtrack",
                            input_summary=f"backtrack to round {snapshot.round_num}",
                            output_summary=f"confidence {confidence:.2f} -> {snapshot.confidence:.2f}",
                        ))
                        consecutive_no_improvement = 0
                        continue

            reflection_guidance = reflection_memory.generate_guidance()
            if not critique.passed:
                reflection = await self._generate_reflection(
                    request.task, current, critique, round_num, model_adapter,
                )
                if reflection:
                    reflection_memory.add_reflection(
                        attempt=round_num,
                        failure_reason=reflection.get("failure_reason", "Unknown failure"),
                        lesson=reflection.get("lesson", "No lesson"),
                        suggested_approach=reflection.get("suggested_approach", "Try differently"),
                    )

            improved = await self._run_improvement(
                request.task, current, critique, reflection_guidance, model_adapter,
            )

            if improved:
                current = improved
                snapshots.append(Snapshot(current, confidence, round_num))
            else:
                break

        if best_content == current and best_critique:
            final_critique = best_critique
        else:
            final_critique = critique if "critique" in dir() else CritiqueResult(scores={})

        elapsed = (time.monotonic() - start) * 1000

        logger.info(
            "deep_refine_complete",
            rounds=len(all_traces),
            best_confidence=best_confidence,
            reflections=reflection_memory.size,
            duration_ms=round(elapsed, 1),
        )

        return [Candidate(
            id="deep_ref_01",
            strategy=self.name,
            path_type="deep_refinement",
            content=best_content,
            reasoning_chain=[rt.output_summary for rt in all_traces],
            confidence=best_confidence,
            critique=final_critique,
            round_created=len(all_traces),
            duration_ms=round(elapsed, 1),
            metadata={"reflections": reflection_memory.size, "snapshots": len(snapshots)},
        )]

    async def _generate_initial(
        self,
        task: str,
        model_adapter: Any,
        context: dict[str, Any],
    ) -> str:
        """Generate initial solution."""
        messages = [
            {"role": "system", "content": DEEP_REFINE_SYSTEM_PROMPT},
            {"role": "user", "content": task},
        ]
        parts: list[str] = []
        async for chunk in model_adapter.stream_chat(messages=messages):
            if chunk.content:
                parts.append(chunk.content)
        return "".join(parts)

    async def _run_critique(
        self,
        task: str,
        content: str,
        model_adapter: Any,
        round_num: int,
        max_rounds: int,
    ) -> CritiqueResult:
        """Run critique on current content."""
        prompt = (
            f"Evaluate this output against the task.\n\nTASK:\n{task}\n\n"
            f"OUTPUT:\n{content}\n\nRound {round_num}/{max_rounds}.\n"
            f"Score 1-5 on: correctness, completeness, clarity, safety, actionability.\n"
            f"Respond with JSON matching this schema:\n{json.dumps(_CRITIQUE_SCHEMA)}"
        )
        messages = [
            {"role": "system", "content": "You are a precise evaluation assistant."},
            {"role": "user", "content": prompt},
        ]
        try:
            result = await model_adapter.chat(
                messages, response_format={"type": "json_object"}, temperature=0.2, max_tokens=2000,
            )
            return _parse_critique_response(result.content)
        except Exception as exc:
            logger.error("deep_refine_critique_error", error=str(exc))
            return CritiqueResult(passed=False, scores={d: 1.0 for d in ("correctness", "completeness", "clarity", "safety", "actionability")})

    async def _generate_reflection(
        self,
        task: str,
        content: str,
        critique: CritiqueResult,
        round_num: int,
        model_adapter: Any,
    ) -> dict[str, str] | None:
        """Generate reflection from failed attempt."""
        issues_text = critique.to_feedback_string() or "Multiple issues found"
        prompt = REFLECTION_GENERATION_PROMPT.format(issues=issues_text, output=content[:2000])
        messages = [
            {"role": "system", "content": "You are a self-reflective reasoning engine."},
            {"role": "user", "content": prompt},
        ]
        try:
            result = await model_adapter.chat(
                messages, response_format={"type": "json_object"}, temperature=0.3, max_tokens=1500,
            )
            data = json.loads(result.content.strip())
            return {
                "failure_reason": data.get("failure_reason", ""),
                "lesson": data.get("lesson", ""),
                "suggested_approach": data.get("suggested_approach", ""),
            }
        except Exception as exc:
            logger.error("deep_refine_reflection_error", error=str(exc))
            return None

    async def _run_improvement(
        self,
        task: str,
        content: str,
        critique: CritiqueResult,
        reflection_guidance: str,
        model_adapter: Any,
    ) -> str | None:
        """Improve content based on critique and reflection."""
        feedback = critique.to_feedback_string()
        if not feedback:
            return None

        reflection_section = ""
        if reflection_guidance:
            reflection_section = f"\n{reflection_guidance}\n"

        prompt = (
            f"TASK:\n{task}\n\n"
            f"{reflection_section}\n"
            f"PREVIOUS OUTPUT:\n{content}\n\n"
            f"CRITIQUE:\n{feedback}\n\n"
            f"Produce an improved output addressing every issue."
        )
        messages = [
            {"role": "system", "content": "You are a skilled revision assistant."},
            {"role": "user", "content": prompt},
        ]
        try:
            result = await model_adapter.chat(messages, temperature=0.5, max_tokens=8000)
            improved = result.content.strip()
            if len(improved) < len(content) * 0.3:
                return None
            return improved
        except Exception as exc:
            logger.error("deep_refine_improve_error", error=str(exc))
            return None

    async def _decide_backtrack(
        self,
        content: str,
        avg_score: float,
        reflection_count: int,
        round_num: int,
        model_adapter: Any,
    ) -> str:
        """Decide whether to backtrack or continue."""
        excerpt = content[:500] if content else ""
        prompt = BACKTRACK_DECISION_PROMPT.format(
            round_num=round_num,
            avg_score=avg_score,
            reflection_count=reflection_count,
            excerpt=excerpt,
        )
        messages = [
            {"role": "system", "content": "You are a strategic reasoning controller."},
            {"role": "user", "content": prompt},
        ]
        try:
            result = await model_adapter.chat(
                messages, response_format={"type": "json_object"}, temperature=0.3, max_tokens=500,
            )
            data = json.loads(result.content.strip())
            return data.get("decision", "continue")
        except Exception:
            return "continue"

    def _should_stop(self, critique: CritiqueResult) -> bool:
        """Check if refinement should stop."""
        if critique.passed and critique.average_score >= 4.0:
            return True
        if critique.average_score >= 4.5 and critique.critical_count == 0:
            return True
        return False

    def _get_model(self, request: ReasoningRequest, model_registry: Any) -> Any:
        """Get model adapter from registry."""
        if request.model_override:
            return model_registry.get_or_create(request.model_override)
        return model_registry.get_default()
