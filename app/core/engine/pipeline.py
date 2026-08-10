"""Pipeline execution engine — reference: OpenSquilla Pipeline pattern.

TurnContext carries immutable-ish state through ordered steps.
Each step can fail-open (log warning, continue with partial data).
Pipeline snapshots support rollback and debugging.
"""

from __future__ import annotations

import asyncio
import copy
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.core import AgentEvent, AgentEventType

try:
    from app.models import ToolDef
except ImportError:

    class ToolDef:  # type: ignore[no-redef]
        """Fallback ToolDef when app.models doesn't export it."""
        name: str = ""
        description: str = ""
        parameters: dict | None = None

logger = structlog.get_logger()

TurnStep = Callable[["TurnContext"], Awaitable["TurnContext"]]


@dataclass
class RoutePlan:
    """Structured routing decision result."""
    target_tier: str = "C1"  # C0-C3
    model: str = ""
    provider: str = ""
    confidence: float = 0.0
    probabilities: dict[str, float] = field(default_factory=dict)
    savings_pct: float = 0.0
    fallback_reason: str | None = None
    route_source: str = "classifier"  # classifier / fallback / user_override / ensemble
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "target_tier": self.target_tier,
            "model": self.model,
            "provider": self.provider,
            "confidence": round(self.confidence, 4),
            "probabilities": self.probabilities,
            "savings_pct": round(self.savings_pct, 2),
            "fallback_reason": self.fallback_reason,
            "route_source": self.route_source,
            "latency_ms": round(self.latency_ms, 2),
        }


@dataclass
class TurnContext:
    """Immutable-ish context for a single Agent turn.

    Steps modify metadata dict to pass state forward.
    Original message/session_id remain unchanged.
    """
    message: str
    session_id: str
    model: str
    provider: str
    api_key: str
    base_url: str | None = None
    system_prompt: str = ""
    tool_defs: list[ToolDef] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_message: str | None = None
    route_plan: RoutePlan | None = None
    max_iterations: int = 10
    mode: str = "act"
    user_id: str = ""
    agent_id: str = ""

    @property
    def effective_message(self) -> str:
        return self.raw_message or self.message

    def with_metadata(self, **kwargs: Any) -> TurnContext:
        """Return new context with updated metadata (non-destructive)."""
        new_ctx = copy.copy(self)
        new_ctx.metadata = {**self.metadata, **kwargs}
        return new_ctx

    def snapshot(self) -> dict[str, Any]:
        """Create a serializable snapshot for debugging/rollback."""
        return {
            "session_id": self.session_id,
            "message": self.message[:200],
            "model": self.model,
            "metadata_keys": list(self.metadata.keys()),
            "route_plan": self.route_plan.to_dict() if self.route_plan else None,
        }


@dataclass
class StepResult:
    """Result of a single pipeline step."""
    step_name: str
    success: bool
    duration_ms: float
    error: str | None = None
    warning: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


class PipelineError(Exception):
    """Raised when pipeline execution cannot continue."""
    def __init__(self, step_name: str, reason: str, partial_ctx: TurnContext | None = None):
        super().__init__(f"Pipeline failed at [{step_name}]: {reason}")
        self.step_name = step_name
        self.reason = reason
        self.partial_ctx = partial_ctx


async def run_pipeline(
    ctx: TurnContext,
    steps: list[tuple[str, TurnStep]],
    *,
    fail_open: bool = True,
    max_step_time: float = 30.0,
) -> tuple[TurnContext, list[StepResult]]:
    """Execute pipeline steps in order.

    Args:
        ctx: Initial turn context
        steps: List of (name, step_callable) pairs
        fail_open: If True, step failures are logged but pipeline continues
        max_step_time: Hard timeout per step in seconds

    Returns:
        Tuple of (final context, list of step results)

    Raises:
        PipelineError: If fail_open=False and a step fails
    """
    results: list[StepResult] = []
    current_ctx = ctx

    for step_name, step_fn in steps:
        start = time.monotonic()
        error = None
        warning = None
        success = True

        try:
            current_ctx = await asyncio.wait_for(step_fn(current_ctx), timeout=max_step_time)
        except TimeoutError:
            success = False
            error = f"Step timeout after {max_step_time}s"
            logger.warning("pipeline.step_timeout", step=step_name, timeout=max_step_time)
        except Exception as e:
            success = False
            error = str(e)
            logger.warning("pipeline.step_error", step=step_name, error=str(e))

        duration = (time.monotonic() - start) * 1000

        if not success and not fail_open:
            raise PipelineError(step_name, error or "unknown", current_ctx)

        if not success and fail_open:
            warning = f"Step {step_name} failed (fail-open): {error}"

        results.append(StepResult(
            step_name=step_name,
            success=success,
            duration_ms=round(duration, 2),
            error=error,
            warning=warning,
        ))

    return current_ctx, results


def build_pipeline_event(results: list[StepResult]) -> AgentEvent:
    """Convert pipeline step results to an AgentEvent for streaming."""
    return AgentEvent(
        type=AgentEventType.PIPELINE_COMPLETE,
        data={
            "steps": [
                {
                    "name": r.step_name,
                    "success": r.success,
                    "duration_ms": r.duration_ms,
                    "error": r.error,
                }
                for r in results
            ],
            "total_steps": len(results),
            "failed_steps": sum(1 for r in results if not r.success),
        },
    )
