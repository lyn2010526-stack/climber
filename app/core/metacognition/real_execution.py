"""Real execution support for the metacognition subsystem.

Supports explicitly injected user-model judgment and sub-task execution:

- Feature switch: ``USER_METACOGNITION_REAL_EXECUTION`` (default on).
  Disabled subtask execution fails closed; hypothesis estimates are labeled.
- Model adapters are explicitly injected by the owning user application.
  Automatic provider/environment credential resolution is never performed.
- Every LLM interaction is bounded (input token cap + wall-clock timeout).
  Subtask failures remain failed; model judgments never certify experiments.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
from dataclasses import dataclass
from typing import Any

import structlog

from app.models import ModelAdapter

logger = structlog.get_logger(__name__)

REAL_EXECUTION_ENV_VAR = "USER_METACOGNITION_REAL_EXECUTION"
DEFAULT_HYPOTHESIS_TOKEN_CAP = 2000
DEFAULT_VERIFICATION_TIMEOUT = 30.0
DEFAULT_EXECUTION_TIMEOUT = 60.0
DEFAULT_MAX_OUTPUT_CHARS = 8000

# Conservative estimate used for prompt budgeting only; exact token counts
# are taken from the adapter response when reported.
_CHARS_PER_TOKEN = 4

_OFF_VALUES = {"0", "false", "no", "off"}

# Fixed instruction overhead reserved from the per-verification token cap.
_PROMPT_MARGIN_TOKENS = 64


class ModelUnavailableError(RuntimeError):
    """Raised when no model adapter can be resolved for real execution."""


@dataclass
class SubTaskExecution:
    output: str
    tokens_used: int
    iterations: int
    status: str = "completed"
    source: str = "executor"
    error: str | None = None


def make_engine_subtask_executor(engine: Any, *, principal: Any, **session_options: Any):
    """Adapt the existing engine interface without bypassing its permission chain."""
    from app.core.evaluation.models import EvalScenario
    from app.core.evaluation.runner import make_engine_agent_fn

    async def execute(goal: str, context: dict[str, Any] | None) -> SubTaskExecution:
        context = context or {}
        runner = make_engine_agent_fn(
            engine,
            principal=principal,
            token_budget=context.get("token_budget", 8000),
            **session_options,
        )
        trajectory = await runner(EvalScenario(name="subtask", user_input=goal), 0)
        return SubTaskExecution(
            trajectory.output,
            trajectory.tokens_used,
            trajectory.metadata["iterations"],
            status=trajectory.status,
            source="engine",
            error=trajectory.error,
        )

    return execute


def real_execution_enabled() -> bool:
    """Whether metacognition should execute for real.

    Defaults to enabled; setting ``USER_METACOGNITION_REAL_EXECUTION`` to
    a falsy value (0/false/no/off) reverts to the heuristic paths.
    """
    raw = os.environ.get(REAL_EXECUTION_ENV_VAR)
    if raw is None:
        return True
    return raw.strip().lower() not in _OFF_VALUES


def estimate_tokens(text: str) -> int:
    """Estimate the token count of a text (4 chars per token)."""
    if not text:
        return 0
    return (len(text) + _CHARS_PER_TOKEN - 1) // _CHARS_PER_TOKEN


def truncate_to_tokens(text: str, token_cap: int) -> str:
    """Truncate text so it fits inside a token budget."""
    max_chars = max(0, token_cap) * _CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def resolve_model_adapter(explicit: ModelAdapter | None = None) -> ModelAdapter | None:
    """Resolve a model adapter for metacognition LLM calls.

    Only explicitly injected user-owned adapters are accepted.
    """
    # Automatic registry defaults may resolve platform/provider environment keys.
    # The owning application must inject its configured user adapter explicitly.
    return explicit


def parse_verdict_json(content: str) -> dict[str, Any]:
    """Parse and validate a verifier JSON payload.

    Accepts JSON embedded in surrounding prose (first "{" to last "}").
    Raises ValueError on malformed or incomplete verdicts so callers fall
    back to the heuristic path instead of trusting junk.
    """
    text = (content or "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("verifier response contains no JSON object")
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError(f"verifier response is not valid JSON: {exc}") from None
    if not isinstance(parsed, dict):
        raise ValueError("verifier response must be a JSON object")
    verdict = str(parsed.get("verdict", "")).strip().lower()
    if not verdict:
        raise ValueError("verifier response missing verdict")
    confidence = float(parsed.get("confidence", 0.0))
    if verdict not in {"feasible", "infeasible", "uncertain"}:
        raise ValueError("verifier response contains an unknown verdict")
    if not math.isfinite(confidence) or not 0 <= confidence <= 1:
        raise ValueError("verifier confidence must be finite and between zero and one")
    return {
        "verdict": verdict,
        "confidence": round(min(1.0, max(0.0, confidence)), 4),
        "reason": str(parsed.get("reason", "")),
    }


class LLMHypothesisVerifier:
    """Default hypothesis evaluator backed by a single bounded LLM call.

    One chat call per hypothesis, JSON-verdict output, hard input token
    cap. Raises on adapter/transport/parse failure so the caller decides
    how to fall back.
    """

    SYSTEM_PROMPT = (
        "You verify execution hypotheses for an autonomous agent. "
        "Given the task goal and one candidate hypothesis (its predicted "
        "next state and estimated cost), judge whether following the "
        "hypothesis is likely to achieve the goal. "
        'Reply with ONLY a JSON object: {"verdict": "feasible" | '
        '"infeasible" | "uncertain", "confidence": <float 0.0-1.0>, '
        '"reason": "<short justification>"}'
    )

    def __init__(
        self,
        adapter: ModelAdapter | None = None,
        token_cap: int = DEFAULT_HYPOTHESIS_TOKEN_CAP,
        timeout: float = DEFAULT_VERIFICATION_TIMEOUT,
    ):
        self._adapter = adapter
        self._token_cap = token_cap
        self._timeout = timeout

    @property
    def token_cap(self) -> int:
        return self._token_cap

    async def __call__(self, hypothesis: dict[str, Any]) -> dict[str, Any]:
        adapter = self._adapter if self._adapter is not None else resolve_model_adapter()
        if adapter is None:
            raise ModelUnavailableError("no model adapter available for hypothesis verification")
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": self._fit_payload(hypothesis)},
        ]
        result = await asyncio.wait_for(
            adapter.chat(messages=messages, tools=None, max_tokens=self._token_cap),
            timeout=self._timeout,
        )
        content = result.content or ""
        if result.tokens_used and result.tokens_used > self._token_cap:
            raise ValueError("hypothesis token budget exceeded")
        return parse_verdict_json(content)

    def _fit_payload(self, hypothesis: dict[str, Any]) -> str:
        """Serialize the hypothesis payload inside the per-call token cap."""
        try:
            payload_text = json.dumps(hypothesis, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            payload_text = str(hypothesis)
        budget = self._token_cap - estimate_tokens(self.SYSTEM_PROMPT) - _PROMPT_MARGIN_TOKENS
        return truncate_to_tokens(payload_text, max(budget, 128))


async def execute_subtask_llm(
    goal: str,
    context: dict[str, Any] | None = None,
    *,
    adapter: ModelAdapter | None = None,
    max_output_chars: int = DEFAULT_MAX_OUTPUT_CHARS,
    timeout: float = DEFAULT_EXECUTION_TIMEOUT,
) -> tuple[str, int]:
    """Run one sub-task as a single bounded LLM turn.

    Args:
        goal: The sub-task goal.
        context: Optional context dict (advisory; dropped when unserializable).
        adapter: Explicit adapter; defaults to the DI ModelRegistry.
        max_output_chars: Hard cap on the returned output text.

    Returns:
        (output_text, tokens_used) from the real model response.

    Raises:
        ModelUnavailableError: When no adapter can be resolved.
        Exception: Transport/model failures propagate to the caller.
    """
    resolved = adapter if adapter is not None else resolve_model_adapter()
    if resolved is None:
        raise ModelUnavailableError("no model adapter available for sub-task execution")
    system = (
        "You are a focused sub-agent worker. Complete the given sub-task "
        "concisely and return only the result."
    )
    parts = [f"Sub-task goal:\n{goal}"]
    if context:
        try:
            parts.append("Context:\n" + json.dumps(context, ensure_ascii=False, default=str))
        except (TypeError, ValueError):
            pass
    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": truncate_to_tokens("\n\n".join(parts), DEFAULT_HYPOTHESIS_TOKEN_CAP),
        },
    ]
    result = await asyncio.wait_for(
        resolved.chat(messages=messages, tools=None, max_tokens=DEFAULT_HYPOTHESIS_TOKEN_CAP),
        timeout,
    )
    output = (result.content or "").strip()[:max_output_chars]
    if not output:
        raise ValueError("model returned empty subtask output")
    return output, int(result.tokens_used or 0)
