"""Output Auditor — self-reflection and goal-alignment verification.

Wraps the SelfRefineLoop into a simple audit pipeline:
1. After Agent produces output, audit it against the original task
2. Multi-dimensional scoring: correctness, completeness, clarity, safety, actionability
3. Goal alignment check: does the output actually address the user's intent?
4. On critical failure, the critique can trigger automatic re-execution
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class AuditResult:
    """Result of output audit."""

    passed: bool
    overall_score: float  # 0.0 - 1.0
    dimension_scores: dict[str, float]
    issues: list[str]
    summary: str
    goal_aligned: bool = True
    recommendation: str = ""  # "accept", "revise", "retry"


@dataclass
class AuditConfig:
    """Configuration for output auditing."""

    enabled: bool = True
    max_rounds: int = 2
    score_threshold: float = 3.5
    auto_retry: bool = True
    audit_on_tool_failure: bool = True


class OutputAuditor:
    """Audits agent output quality and goal alignment."""

    def __init__(self, config: AuditConfig | None = None) -> None:
        self._config = config or AuditConfig()

    async def audit(
        self,
        task: str,
        output: str,
        model_adapter: Any,
        context: dict[str, Any] | None = None,
    ) -> AuditResult:
        """Audit agent output against the original task.

        Args:
            task: The original user request / task description.
            output: The agent's response to audit.
            model_adapter: Adapter to call LLM for critique.
            context: Additional context (conversation history, constraints, etc.)

        Returns:
            AuditResult with pass/fail, scores, and recommendations.
        """
        if not self._config.enabled:
            return AuditResult(
                passed=True,
                overall_score=1.0,
                dimension_scores={},
                issues=[],
                summary="Audit disabled",
            )

        if not output or not output.strip():
            return AuditResult(
                passed=False,
                overall_score=0.0,
                dimension_scores={},
                issues=["Empty output"],
                summary="Agent produced no output",
                recommendation="retry",
            )

        try:
            from app.core.reasoning.components.self_refine import SelfRefineLoop

            refine_loop = SelfRefineLoop()

            _, critique, traces = await refine_loop.refine(
                task=task,
                initial=output,
                model_adapter=model_adapter,
                max_rounds=self._config.max_rounds,
                score_threshold=self._config.score_threshold,
            )

            avg_score = critique.average_score if hasattr(critique, "average_score") else 3.0
            overall = avg_score / 5.0

            dimension_scores = {
                d: s / 5.0 for d, s in critique.scores.items()
            } if critique.scores else {}

            issues = [
                f"[{i.severity.value}] {i.description}"
                for i in critique.issues
            ] if critique.issues else []

            goal_aligned = self._check_goal_alignment(task, output, context or {})

            if not critique.passed and self._config.auto_retry:
                recommendation = "retry"
            elif not critique.passed:
                recommendation = "revise"
            else:
                recommendation = "accept"

            result = AuditResult(
                passed=critique.passed and goal_aligned,
                overall_score=overall,
                dimension_scores=dimension_scores,
                issues=issues,
                summary=critique.summary,
                goal_aligned=goal_aligned,
                recommendation=recommendation,
            )

            logger.info(
                "output_audit_complete",
                passed=result.passed,
                score=round(overall, 2),
                goal_aligned=goal_aligned,
                rounds=len(traces),
            )

            return result

        except Exception as e:
            logger.warning("output_audit_error", error=str(e))
            return AuditResult(
                passed=True,  # Fail open — don't block on audit errors
                overall_score=0.5,
                dimension_scores={},
                issues=[],
                summary=f"Audit error: {e}",
                recommendation="accept",
            )

    def _check_goal_alignment(
        self, task: str, output: str, context: dict[str, Any],
    ) -> bool:
        """Lightweight heuristic check: does output address key terms from task?"""
        task_lower = task.lower()
        output_lower = output.lower()

        task_words = set(task_lower.split())
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "shall",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "out", "off", "over", "under", "again",
            "further", "then", "once", "and", "but", "or", "nor", "not",
            "so", "than", "too", "very", "just", "about", "this", "that",
            "these", "those", "it", "its", "i", "me", "my", "we", "our",
            "you", "your", "he", "him", "his", "she", "her", "they",
            "them", "their", "what", "which", "who", "when", "where",
            "why", "how", "all", "each", "every", "both", "few", "more",
            "most", "other", "some", "such", "no", "only", "own", "same",
        }
        key_words = {w for w in task_words if w not in stop_words and len(w) > 3}

        if not key_words:
            return True

        matched = sum(1 for w in key_words if w in output_lower)
        ratio = matched / len(key_words)

        return ratio >= 0.3


_auditor: OutputAuditor | None = None


def get_output_auditor(config: AuditConfig | None = None) -> OutputAuditor:
    global _auditor
    if _auditor is None:
        _auditor = OutputAuditor(config)
    return _auditor
