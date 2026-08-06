"""Self-Refine vertical-depth refinement loop.

Implements the Self-Refine pattern (Google, 2023) with multi-dimensional
scoring and iterative improvement. Extends toward Reflexion (MIT, NeurIPS 2023)
via persistent critique memory across rounds.
"""

from __future__ import annotations

import json
import time
from typing import Any

import structlog
from pydantic import ValidationError

from app.core.reasoning.base import (
    CritiqueResult,
    Issue,
    IssueSeverity,
    RoundTrace,
)

logger = structlog.get_logger()

_DIMENSIONS = ("correctness", "completeness", "clarity", "safety", "actionability")

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
                    "severity": {
                        "type": "string",
                        "enum": ["critical", "major", "minor", "info"],
                    },
                    "description": {"type": "string"},
                    "location": {"type": "string"},
                    "fix_suggestion": {"type": "string"},
                },
            },
        },
    },
}


def _build_critique_prompt(task: str, content: str, round_num: int, max_rounds: int) -> str:
    return (
        f"You are a rigorous evaluator. Assess the following output against the task.\n\n"
        f"TASK:\n{task}\n\n"
        f"OUTPUT:\n{content}\n\n"
        f"This is refinement round {round_num} of {max_rounds}.\n\n"
        f"Evaluate on these dimensions (1-5 scale each):\n"
        f"- correctness: factual accuracy and logical soundness\n"
        f"- completeness: coverage of all task requirements\n"
        f"- clarity: readability and organization\n"
        f"- safety: absence of harmful or risky content\n"
        f"- actionability: practical usability of the output\n\n"
        f"Respond with a JSON object matching this schema:\n"
        f"{json.dumps(_CRITIQUE_SCHEMA, indent=2)}\n\n"
        f'Set "passed" to true only if all scores >= 4 and no critical issues exist.'
    )


def _build_improve_prompt(task: str, content: str, feedback: str) -> str:
    return (
        f"Revise the following output based on the critique.\n\n"
        f"TASK:\n{task}\n\n"
        f"CURRENT OUTPUT:\n{content}\n\n"
        f"CRITIQUE:\n{feedback}\n\n"
        f"Address every issue raised. Preserve strengths while fixing weaknesses.\n"
        f"Return only the improved output — no preamble, no explanation."
    )


def _parse_critique_response(raw: str) -> CritiqueResult:
    """Parse LLM response into CritiqueResult, with fallback extraction."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    if cleaned.startswith("json"):
        cleaned = cleaned[4:].strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            return CritiqueResult(
                passed=False,
                summary="Failed to parse critique response",
                scores={d: 1.0 for d in _DIMENSIONS},
                issues=[
                    Issue(
                        severity=IssueSeverity.MAJOR,
                        description="Critique returned unparseable output",
                    )
                ],
            )
        data = json.loads(cleaned[start : end + 1])

    issues = []
    for raw_issue in data.get("issues", []):
        try:
            issues.append(
                Issue(
                    severity=IssueSeverity(raw_issue.get("severity", "minor")),
                    description=raw_issue.get("description", "Unspecified issue"),
                    location=raw_issue.get("location", ""),
                    fix_suggestion=raw_issue.get("fix_suggestion", ""),
                )
            )
        except (ValueError, ValidationError):
            continue

    scores = {}
    raw_scores = data.get("scores", {})
    for dim in _DIMENSIONS:
        val = raw_scores.get(dim, 3.0)
        try:
            scores[dim] = float(max(1.0, min(5.0, val)))
        except (TypeError, ValueError):
            scores[dim] = 3.0

    return CritiqueResult(
        passed=bool(data.get("passed", False)),
        summary=data.get("summary", ""),
        scores=scores,
        issues=issues,
    )


class SelfRefineLoop:
    """Iterative self-refinement loop with multi-dimensional critique.

    Each round produces a critique (structured evaluation) and an improvement
    (revised output). The loop terminates when the critique passes or the
    maximum round count is reached.
    """

    async def refine(
        self,
        task: str,
        initial: str,
        model_adapter: Any,
        path_type: str = "default",
        max_rounds: int = 3,
        score_threshold: float = 3.5,
    ) -> tuple[str, CritiqueResult, list[RoundTrace]]:
        """Run the self-refinement loop.

        Returns:
            Tuple of (refined_content, final_critique, round_traces).
        """
        current = initial
        traces: list[RoundTrace] = []
        final_critique = CritiqueResult(scores={d: 0.0 for d in _DIMENSIONS})

        for round_num in range(1, max_rounds + 1):
            round_start = time.monotonic()

            critique = await self._run_critique(
                task=task,
                content=current,
                model_adapter=model_adapter,
                round_num=round_num,
                max_rounds=max_rounds,
                path_type=path_type,
                traces=traces,
            )

            final_critique = critique

            if self._should_stop(critique, score_threshold):
                logger.info(
                    "Self-refine converged",
                    round=round_num,
                    avg_score=critique.average_score,
                )
                break

            if round_num == max_rounds:
                break

            improved = await self._run_improvement(
                task=task,
                content=current,
                critique=critique,
                model_adapter=model_adapter,
                path_type=path_type,
                traces=traces,
            )

            if improved:
                current = improved
            else:
                logger.warning(
                    "Self-refine improvement failed, retaining current",
                    round=round_num,
                )
                break

            _ = time.monotonic() - round_start

        return current, final_critique, traces

    async def _run_critique(
        self,
        task: str,
        content: str,
        model_adapter: Any,
        round_num: int,
        max_rounds: int,
        path_type: str,
        traces: list[RoundTrace],
    ) -> CritiqueResult:
        prompt = _build_critique_prompt(task, content, round_num, max_rounds)
        messages = [
            {"role": "system", "content": "You are a precise evaluation assistant."},
            {"role": "user", "content": prompt},
        ]

        start = time.monotonic()
        try:
            result = await model_adapter.chat(
                messages,
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=2000,
            )
            raw = result.content
        except Exception as exc:
            logger.error(
                "Critique LLM call failed",
                round=round_num,
                error=str(exc),
                provider=getattr(model_adapter, "provider", "unknown"),
            )
            duration = (time.monotonic() - start) * 1000
            traces.append(
                RoundTrace(
                    round_num=round_num,
                    action="critique_error",
                    input_summary=task[:100],
                    output_summary=f"LLM error: {type(exc).__name__}",
                    duration_ms=duration,
                )
            )
            return CritiqueResult(
                passed=False,
                summary=f"Critique failed: {type(exc).__name__}",
                scores={d: 1.0 for d in _DIMENSIONS},
            )

        duration = (time.monotonic() - start) * 1000
        critique = _parse_critique_response(raw)

        traces.append(
            RoundTrace(
                round_num=round_num,
                action="critique",
                input_summary=task[:100],
                output_summary=(
                    f"passed={critique.passed}, "
                    f"avg={critique.average_score:.2f}, "
                    f"issues={len(critique.issues)}"
                ),
                duration_ms=duration,
            )
        )

        logger.debug(
            "Critique complete",
            round=round_num,
            passed=critique.passed,
            scores=critique.scores,
        )

        return critique

    async def _run_improvement(
        self,
        task: str,
        content: str,
        critique: CritiqueResult,
        model_adapter: Any,
        path_type: str,
        traces: list[RoundTrace],
    ) -> str | None:
        feedback = critique.to_feedback_string()
        if not feedback:
            return None

        prompt = _build_improve_prompt(task, content, feedback)
        messages = [
            {"role": "system", "content": "You are a skilled revision assistant."},
            {"role": "user", "content": prompt},
        ]

        start = time.monotonic()
        try:
            result = await model_adapter.chat(
                messages,
                temperature=0.5,
                max_tokens=8000,
            )
            improved = result.content.strip()
        except Exception as exc:
            logger.error(
                "Improvement LLM call failed",
                error=str(exc),
                provider=getattr(model_adapter, "provider", "unknown"),
            )
            duration = (time.monotonic() - start) * 1000
            traces.append(
                RoundTrace(
                    round_num=len(traces) + 1,
                    action="improve_error",
                    input_summary=task[:100],
                    output_summary=f"LLM error: {type(exc).__name__}",
                    duration_ms=duration,
                )
            )
            return None

        duration = (time.monotonic() - start) * 1000
        traces.append(
            RoundTrace(
                round_num=len(traces) + 1,
                action="improve",
                input_summary=task[:100],
                output_summary=f"length={len(improved)}",
                duration_ms=duration,
            )
        )

        if len(improved) < len(content) * 0.3:
            logger.warning(
                "Improvement suspiciously short, rejecting",
                original_len=len(content),
                improved_len=len(improved),
            )
            return None

        return improved

    def _should_stop(self, critique: CritiqueResult, threshold: float) -> bool:
        if critique.critical_count > 0:
            return False
        if critique.passed and critique.average_score >= threshold:
            return True
        return bool(critique.average_score >= 4.5 and critique.major_count == 0)
