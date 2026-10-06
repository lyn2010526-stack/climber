"""Rubric judges: deterministic offline judge and LLM-as-a-Judge hook.

The judge is injectable: any callable with the ``Judge`` protocol
signature can be passed to the runner. ``DeterministicJudge`` needs no
LLM and keeps tests fully offline. ``LLMRubricJudge`` resolves an
adapter through the project's ``ModelRegistry`` using user-project
environment variables (``USER_`` prefixed); agent-environment variables
are never read.
"""

from __future__ import annotations

import json
import os
from typing import Any, Protocol

from app.core.evaluation.models import (
    EvaluationResult,
    ItemVerdict,
    RubricItem,
    Trajectory,
)


class Judge(Protocol):
    """Judge protocol: (trajectory, rubric) -> EvaluationResult (sync or async)."""

    def __call__(
        self,
        trajectory: Trajectory,
        rubric: list[RubricItem],
        *,
        scenario_id: str = "",
        expected_points: list[str] | None = None,
    ) -> EvaluationResult | Any: ...


def _transcript(trajectory: Trajectory) -> str:
    """Full transcript: final output plus every call's name, args and output."""
    parts = [trajectory.output or ""]
    for call in trajectory.calls:
        parts.append(call.name or "")
        if call.arguments:
            parts.append(json.dumps(call.arguments, ensure_ascii=False, default=str))
        parts.append(call.output or "")
    return "\n".join(parts).lower()


class DeterministicJudge:
    """Keyword-set judge, fully offline and reproducible.

    Each rubric item passes iff the transcript contains at least one
    ``contains_any`` keyword (case-insensitive) and none of the
    ``not_contains_any`` keywords. The score is the weighted mean of item
    verdicts; an essential failure marks the case failed and a veto
    failure zeroes the score.
    """

    name = "deterministic"

    def judge(
        self,
        trajectory: Trajectory,
        rubric: list[RubricItem],
        *,
        scenario_id: str = "",
        expected_points: list[str] | None = None,
    ) -> EvaluationResult:
        del expected_points
        transcript = _transcript(trajectory)
        verdicts: list[ItemVerdict] = []
        for item in rubric:
            passed = True
            reason = ""
            if item.contains_any and not any(k.lower() in transcript for k in item.contains_any):
                passed = False
                reason = "missing acceptable content"
            if passed:
                for keyword in item.not_contains_any:
                    if keyword.lower() in transcript:
                        passed = False
                        reason = f"forbidden content present: {keyword!r}"
                        break
            if passed and not item.contains_any and not item.not_contains_any:
                passed = False
                reason = "criterion requires an injected judge; no deterministic evidence"
            verdicts.append(
                ItemVerdict(
                    item_id=item.item_id,
                    passed=passed,
                    reason=reason,
                    weight=item.weight,
                    essential=item.essential,
                    veto=item.veto,
                )
            )
        return _aggregate(
            scenario_id=scenario_id or trajectory.scenario_id,
            verdicts=verdicts,
            judge=self.name,
        )


class LLMRubricJudge:
    """LLM-as-a-Judge over the rubric, resolved via ModelRegistry.

    The adapter is fetched lazily on first use so importing this module
    stays side-effect free. Model and key material come from user-project
    environment variables only (``USER_LLM_MODEL`` / ``USER_LLM_API_KEY``
    / ``USER_LLM_BASE_URL``).
    """

    name = "llm-judge"

    def __init__(
        self,
        model_spec: str = "",
        registry: Any = None,
        prompt: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self._model_spec = model_spec or os.environ.get("USER_LLM_MODEL", "")
        self._registry = registry
        self._prompt = prompt or LLM_JUDGE_PROMPT
        self._base_url = (
            base_url if base_url is not None else os.environ.get("USER_LLM_BASE_URL") or None
        )
        self._api_key = api_key if api_key is not None else os.environ.get("USER_LLM_API_KEY", "")
        self._adapter: Any = None

    def _get_adapter(self) -> Any:
        if self._adapter is not None:
            return self._adapter
        registry = self._registry
        if registry is None:
            from app.models.registry import ModelRegistry

            registry = ModelRegistry()
        if not self._api_key:
            raise ValueError("user-provided evaluation API key is required")
        spec = self._model_spec or "openai:gpt-4o-mini"
        provider, sep, model_id = spec.partition(":")
        if not sep:
            # Bare spec (alias such as "gpt-4o-mini"): let the registry
            # resolve provider and model through its alias table.
            self._adapter = registry.get_or_create(
                spec, model_id=spec, api_key=self._api_key, base_url=self._base_url
            )
        else:
            self._adapter = registry.get_or_create(
                provider,
                model_id=model_id,
                api_key=self._api_key,
                base_url=self._base_url,
            )
        return self._adapter

    async def judge(
        self,
        trajectory: Trajectory,
        rubric: list[RubricItem],
        *,
        scenario_id: str = "",
        expected_points: list[str] | None = None,
    ) -> EvaluationResult:
        payload = {
            "user_input": trajectory.user_input,
            "final_output": trajectory.output,
            "expected_points": expected_points or [],
            "calls": [
                {"kind": c.kind, "name": c.name, "arguments": c.arguments, "output": c.output}
                for c in trajectory.calls
            ],
            "rubric": [
                {
                    "item_id": i.item_id,
                    "description": i.description,
                    "essential": i.essential,
                    "veto": i.veto,
                }
                for i in rubric
            ],
        }
        messages = [
            {"role": "system", "content": self._prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        try:
            adapter = self._get_adapter()
            response = await adapter.chat(messages)
            content = getattr(response, "content", "") or ""
        except Exception as exc:  # judge outage must fail closed, not crash the run
            verdicts = [
                ItemVerdict(
                    item_id=i.item_id,
                    passed=False,
                    reason=f"judge call failed: {exc}",
                    weight=i.weight,
                    essential=i.essential,
                    veto=i.veto,
                )
                for i in rubric
            ]
            return _aggregate(
                scenario_id=scenario_id or trajectory.scenario_id,
                verdicts=verdicts,
                judge=self.name,
            )
        verdicts = self._parse_verdicts(content, rubric)
        return _aggregate(
            scenario_id=scenario_id or trajectory.scenario_id,
            verdicts=verdicts,
            judge=self.name,
        )

    def _parse_verdicts(self, content: str, rubric: list[RubricItem]) -> list[ItemVerdict]:
        """Parse the judge JSON; unparseable or missing items fail closed."""
        parsed: dict[str, dict[str, Any]] = {}
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                for entry in data.get("verdicts", []):
                    if isinstance(entry, dict) and entry.get("item_id"):
                        parsed[str(entry["item_id"])] = entry
        except (json.JSONDecodeError, AttributeError):
            parsed = {}
        verdicts: list[ItemVerdict] = []
        for item in rubric:
            entry = parsed.get(item.item_id)
            if entry is None:
                verdicts.append(
                    ItemVerdict(
                        item_id=item.item_id,
                        passed=False,
                        reason="missing judge verdict; fail closed",
                        weight=item.weight,
                        essential=item.essential,
                        veto=item.veto,
                    )
                )
                continue
            verdicts.append(
                ItemVerdict(
                    item_id=item.item_id,
                    passed=entry.get("passed") is True,
                    reason=str(entry.get("reason", "")),
                    weight=item.weight,
                    essential=item.essential,
                    veto=item.veto,
                )
            )
        return verdicts


LLM_JUDGE_PROMPT = """You are a strict evaluation judge for an AI agent trajectory.
Given a user input, the agent's final output, its tool-call transcript, expected
points and a rubric, decide for EVERY rubric item whether the trajectory passes.
Rules:
- Judge only from the provided evidence; do not assume hidden behavior.
- A pass requires the described behavior to be clearly observable.
- Reply with ONLY a JSON object using this schema:
  {"verdicts": [{"item_id": "...", "passed": true/false, "reason": "..."}]}
- Every rubric item must have exactly one verdict.
"""


def _aggregate(*, scenario_id: str, verdicts: list[ItemVerdict], judge: str) -> EvaluationResult:
    """Fold item verdicts into score/pass with essential and veto semantics.

    Score: weighted mean of item verdicts. Pass: no essential failure and
    no veto failure. A veto failure additionally zeroes the score.
    """
    total_weight = sum(v.weight for v in verdicts)
    earned = sum(v.weight for v in verdicts if v.passed)
    score = earned / total_weight if total_weight > 0 else 0.0
    veto_failed = any(v.veto and not v.passed for v in verdicts)
    essential_failed = any(v.essential and not v.passed for v in verdicts)
    if veto_failed:
        score = 0.0
    failure_reasons = [f"{v.item_id}: {v.reason}" for v in verdicts if not v.passed and v.reason]
    return EvaluationResult(
        scenario_id=scenario_id,
        score=round(score, 4),
        passed=bool(verdicts) and not veto_failed and not essential_failed and earned > 0,
        verdicts=verdicts,
        failure_reasons=failure_reasons,
        judge=judge,
    )


# Default offline judge used by the runner when none is injected.
DEFAULT_JUDGE = DeterministicJudge()
