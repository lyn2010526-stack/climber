"""LLM review sub-agent — scientific judgment on top of the deterministic probes.

Implements the AgentLaboratory 评审校验员: after the convergence probes
pass, a second LLM sub-agent reads the experiment spec, the parameters
used, the raw tool output and the probe metrics, and returns a verdict.
This catches things probes cannot: semantically wrong results, physics that
"converges" to an implausible value, or parameter ranges that betray the
goal.

The LLM judgment is a *downgrade-only* gate: it can reject or ask for a
retry, but it can never accept what the deterministic layer rejected, and
it cannot cause new tool dispatch beyond the existing round budget. On any
LLM failure (exception, timeout, unparseable reply) it returns RETRY so
the harness just moves to the next round instead of mislabeling a result.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from app.simulation.models import Verdict
from app.simulation.review import ReviewContext

logger = structlog.get_logger()

LLMReviewCall = Callable[[str, str], Awaitable[str]]

_SYSTEM_PROMPT = (
    "You are a rigorous scientific review judge. You verify whether a "
    "simulation result is physically and numerically plausible given the "
    "goal, the parameters, and the raw output. Respond with a single JSON "
    "object:\n"
    "{\"verdict\": \"accepted\" | \"rejected\" | \"retry\", "
    "\"reason\": \"<one sentence>\"}\n"
    "Use 'rejected' for clearly wrong values, 'retry' when you cannot "
    "judge or the run seems inconclusive, 'accepted' only when you are "
    "confident the result is sound."
)

_USER_TEMPLATE = (
    "Goal: {goal}\n"
    "Tool: {tool_name}\n"
    "Parameters: {parameters}\n"
    "Raw output:\n{output}\n"
    "Probe metrics: {probe_metrics}\n\n"
    "Emit the verdict JSON now."
)


def _parse_verdict(text: str) -> Verdict | None:
    """Extract a Verdict from the LLM reply."""
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text
    match = re.search(r"\{.*\}", candidate, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    verdict = parsed.get("verdict") if isinstance(parsed, dict) else None
    try:
        return Verdict(verdict)
    except ValueError:
        return None


class LLMReviewer:
    """Async review callback that consults an LLM sub-agent."""

    def __init__(
        self,
        llm_call: LLMReviewCall,
        prefer_retry_on_failure: bool = True,
        log_failures: bool = False,
    ):
        self._llm_call = llm_call
        self._prefer_retry_on_failure = prefer_retry_on_failure
        self._log_failures = log_failures

    async def __call__(self, ctx: ReviewContext) -> Verdict:
        prompt = _USER_TEMPLATE.format(
            goal=ctx.spec.objective or ctx.spec.description or "untitled experiment",
            tool_name=ctx.spec.tool_name,
            parameters=json.dumps(ctx.attempt.parameters, ensure_ascii=False, default=str),
            output=(ctx.attempt.output or "")[:4000],
            probe_metrics=json.dumps(ctx.attempt.probe.metrics, ensure_ascii=False, default=str)
            if ctx.attempt.probe else "{}",
        )
        try:
            reply = await self._llm_call(prompt, _SYSTEM_PROMPT)
        except Exception as e:
            return self._on_failure(f"llm_review_call_failed: {e}")
        verdict = _parse_verdict(reply)
        if verdict is None:
            return self._on_failure("llm_review_unparseable")
        return verdict

    def _on_failure(self, reason: str) -> Verdict:
        if self._log_failures:
            logger.warning("llm_review_failure", reason=reason)
        return Verdict.RETRY if self._prefer_retry_on_failure else Verdict.REJECTED