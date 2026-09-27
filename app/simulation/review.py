"""Reviewer — validation gate between tool execution and the next round.

Combines two reference patterns:

- Safe-Lab-Agents: a parameter allowlist/allow-list is applied *before*
  the tool is called, rejecting dangerous or out-of-scope parameters.
- AgentLaboratory: the result is judged by probes (and optionally an LLM
  sub-agent) and marked accepted/rejected before it feeds the next round.

The reviewer is deterministic by default and does not require an LLM, so
it can be unit-tested and used headless.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from app.simulation.models import (
    ExperimentAttempt,
    ExperimentReport,
    ExperimentSpec,
    Verdict,
)
from app.simulation.probes import probe_convergence

ReviewFn = Callable[["ReviewContext"], Awaitable[Verdict]]


@dataclass
class ParameterPolicy:
    """Safe-Lab style parameter allowlist for a tool.

    ``allowed`` restricts which parameter names may be passed; ``ranges``
    declares numeric bounds per parameter; ``disallowed_values`` rejects
    specific dangerous values (e.g. exec flags). Name allowlist can be
    disabled by passing ``allowed=None``.
    """
    allowed: list[str] | None = None
    ranges: dict[str, tuple[float | None, float | None]] = field(default_factory=dict)
    disallowed_values: dict[str, list[Any]] = field(default_factory=dict)
    require: list[str] = field(default_factory=list)

    def validate(self, parameters: dict[str, Any]) -> tuple[bool, str]:
        for required in self.require:
            if required not in parameters:
                return False, f"required parameter '{required}' missing"

        if self.allowed is not None:
            unknown = set(parameters) - set(self.allowed)
            if unknown:
                name = sorted(unknown)[0]
                return False, f"parameter '{name}' is not allowed"

        for key, value in parameters.items():
            if key in self.disallowed_values and value in self.disallowed_values[key]:
                return False, f"parameter '{key}' has a disallowed value: {value!r}"
            if key in self.ranges and isinstance(value, (int, float)):
                lo, hi = self.ranges[key]
                if lo is not None and value < lo:
                    return False, f"parameter '{key}' below min {lo}"
                if hi is not None and value > hi:
                    return False, f"parameter '{key}' above max {hi}"
        return True, ""


@dataclass
class ReviewContext:
    """Everything the reviewer needs to judge one attempt."""
    spec: ExperimentSpec
    attempt: ExperimentAttempt
    policy: ParameterPolicy | None = None
    expect_numbers: bool = True
    metric_keys: list[str] | None = None
    min_value: float | None = None
    max_value: float | None = None


class HarnessReviewer:
    """Deterministic reviewer: parameter policy + convergence probes.

    ``extra_review`` may be injected as an optional async callback that
    receives the ReviewContext and returns a Verdict; the deterministic
    result is overridden only when deterministic checks pass and the
    callback returns REJECTED (so a rejected run is never silently
    accepted by probes alone).
    """

    def __init__(self, extra_review: ReviewFn | None = None):
        self._extra_review = extra_review

    async def review(self, ctx: ReviewContext) -> ReviewContext:
        attempt = ctx.attempt

        if ctx.policy is not None:
            ok, reason = ctx.policy.validate(attempt.parameters)
            if not ok:
                attempt.verdict = Verdict.REJECTED
                attempt.reviewer_note = f"policy: {reason}"
                return ctx

        if not attempt.success:
            attempt.verdict = Verdict.REJECTED
            attempt.reviewer_note = f"tool: {attempt.error or 'execution failed'}"
            return ctx

        probe = probe_convergence(
            attempt.output,
            expect_numbers=ctx.expect_numbers,
            metric_keys=ctx.metric_keys,
            metrics=_parse_json_output(attempt.output),
            min_value=ctx.min_value,
            max_value=ctx.max_value,
        )
        attempt.probe = probe
        if not probe.ok:
            attempt.verdict = Verdict.REJECTED
            attempt.reviewer_note = f"probe: {probe.reason}"
            return ctx

        if self._extra_review is not None:
            verdict = await self._extra_review(ctx)
            if verdict == Verdict.REJECTED:
                attempt.verdict = Verdict.REJECTED
                attempt.reviewer_note = "llm-reviewer: rejected"
                return ctx
            if verdict == Verdict.RETRY:
                attempt.verdict = Verdict.RETRY
                attempt.reviewer_note = "llm-reviewer: retry"
                return ctx

        attempt.verdict = Verdict.ACCEPTED
        attempt.reviewer_note = "ok"
        return ctx


def _parse_json_output(output: str) -> dict[str, Any] | None:
    """Best-effort parse of a JSON-structured tool result."""
    if not output:
        return None
    try:
        parsed = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def metrics_from_report(report: ExperimentReport) -> dict[str, Any]:
    """Extract named metrics from the accepted attempt, if available."""
    if report.accepted_attempt is None:
        return {}
    return report.accepted_attempt.probe.metrics
