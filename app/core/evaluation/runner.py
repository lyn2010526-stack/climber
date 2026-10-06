"""Evaluation runner: execute scenarios, capture trajectories, score, aggregate.

The runner is agent-agnostic: ``agent_fn`` is injected so tests and the
API can plug any execution path. The default factory wraps the engine's
``run_agent`` streaming loop and records tool calls, tokens and output
into a :class:`Trajectory`.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import aclosing
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from app.core.evaluation.judges import DEFAULT_JUDGE, DeterministicJudge
from app.core.evaluation.models import (
    CallRecord,
    EvalScenario,
    EvaluationReport,
    EvaluationResult,
    RubricItem,
    ScenarioReport,
    Trajectory,
)

# agent_fn(scenario, candidate_index) -> Trajectory
AgentFn = Callable[[EvalScenario, int], Awaitable[Trajectory]]

# An injectable judge: either a plain callable or an object exposing ``judge``.
JudgeLike = Callable[..., EvaluationResult] | DeterministicJudge


def pass_at_k(n: int, c: int, k: int) -> float:
    """Unbiased pass@k estimator (Chen et al.): probability that at least
    one of ``k`` sampled candidates passes when ``c`` of ``n`` run pass.
    """
    if n <= 0 or not 0 <= c <= n or not 1 <= k <= n:
        raise ValueError("require n > 0, 0 <= c <= n and 1 <= k <= n")
    if n - c < k:
        return 1.0
    probability = 1.0
    for i in range(k):
        probability *= (n - c - i) / (n - i)
    return 1.0 - probability


def pass_hat_k(n: int, c: int, k: int) -> float:
    """Pass^k estimator (business reliability): probability that ``k``
    consecutive candidates all pass, assuming per-run pass rate ``c/n``.
    """
    if n <= 0 or not 0 <= c <= n or k <= 0:
        raise ValueError("require n > 0, 0 <= c <= n and k > 0")
    rate = c / n
    return rate**k


async def evaluate_trajectory(
    trajectory: Trajectory,
    rubric: list[RubricItem],
    judge: JudgeLike | None = None,
    *,
    scenario_id: str = "",
    expected_points: list[str] | None = None,
) -> EvaluationResult:
    """Score one trajectory against a rubric with an injectable judge.

    The default judge is the deterministic keyword-set judge; an async
    judge (e.g. LLMRubricJudge) is awaited transparently.
    """
    judge = judge or DEFAULT_JUDGE
    judge_fn = judge if callable(judge) else judge.judge
    result: Any = judge_fn(
        trajectory,
        rubric,
        scenario_id=scenario_id or trajectory.scenario_id,
        expected_points=expected_points,
    )
    if hasattr(result, "__await__"):
        result = await result
    if trajectory.error or trajectory.status != "completed":
        result.score = 0.0
        result.passed = False
        result.failure_reasons.append(f"trajectory failed: {trajectory.error or trajectory.status}")
    return cast(EvaluationResult, result)


def make_engine_agent_fn(
    engine: Any,
    *,
    provider: str = "openai",
    model_id: str = "gpt-4o",
    api_key: str = "",
    base_url: str | None = None,
    system_prompt: str | None = None,
    agent_id: str = "eval-agent",
    user_id: str | None = None,
    principal: Any = None,
    permission_config: Any = None,
    token_budget: int = 8000,
) -> AgentFn:
    """Wrap the engine streaming run into an eval agent_fn.

    Each candidate gets a fresh session; the agent event stream is folded
    into a Trajectory with call records, tokens, output and error status.
    """
    from app.core import AgentEventType

    async def _run_impl(scenario: EvalScenario, candidate_index: int) -> Trajectory:
        from app.core.principal import get_context_principal

        owner = principal or get_context_principal()
        if user_id is not None and user_id != owner.subject_id:
            raise ValueError("evaluation user_id must match principal")
        session = engine.create_session(
            agent_id=agent_id,
            user_id=owner.subject_id,
            provider=provider,
            model_id=model_id,
            api_key=api_key,
            base_url=base_url,
            system_prompt=system_prompt,
        )
        session.principal = owner
        if permission_config is not None:
            session.permission_config = permission_config
        async with aclosing(engine.run(session, scenario.user_input)) as events:
            return await _consume(events, session, scenario, candidate_index, owner)

    async def _consume(
        events: AsyncIterator[Any],
        session: Any,
        scenario: EvalScenario,
        candidate_index: int,
        owner: Any,
    ) -> Trajectory:
        calls: list[CallRecord] = []
        output_parts: list[str] = []
        tokens = 0
        status = "failed"
        error: str | None = None
        step = 0
        async for event in events:
            data = event.data or {}
            if event.type == AgentEventType.TEXT:
                content = data.get("content", "")
                if content:
                    calls.append(
                        CallRecord(step=step, kind="llm", name=session.model_id, output=content)
                    )
                    step += 1
                    output_parts.append(content)
            elif event.type == AgentEventType.TOOL_CALL:
                calls.append(
                    CallRecord(
                        step=step,
                        kind="tool",
                        name=data.get("name", ""),
                        arguments=data.get("arguments", {}),
                    )
                )
                step += 1
            elif event.type == AgentEventType.TOOL_RESULT:
                calls.append(
                    CallRecord(
                        step=step,
                        kind="tool",
                        name=data.get("name", ""),
                        output=str(data.get("result", data.get("content", ""))),
                    )
                )
                step += 1
            elif event.type == AgentEventType.DONE:
                tokens = data.get("tokens_used", tokens)
                status = data.get("status", "completed")
            elif event.type == AgentEventType.ERROR:
                error = data.get("error", "unknown error")
            tokens = max(tokens, getattr(session, "_run_tokens", 0))
            if tokens > token_budget:
                error = "token budget exceeded"
                if hasattr(session, "stop"):
                    session.stop()
                break
        if error:
            status = "failed"
        return Trajectory(
            scenario_id=scenario.scenario_id,
            user_input=scenario.user_input,
            output="".join(output_parts),
            calls=calls,
            tokens_used=tokens,
            status=status,
            error=error,
            metadata={
                "candidate_index": candidate_index,
                "session_id": session.session_id,
                "iterations": getattr(session, "iteration", 0),
                "execution_source": "engine",
                "principal": owner.identity_key,
            },
        )

    async def _run(scenario: EvalScenario, candidate_index: int) -> Trajectory:
        from app.core.principal import (
            get_context_principal,
            reset_current_principal,
            set_current_principal,
        )

        token = set_current_principal(principal or get_context_principal())
        try:
            return await _run_impl(scenario, candidate_index)
        finally:
            reset_current_principal(token)

    return _run


def _fake_error_trajectory(
    scenario: EvalScenario, candidate_index: int, exc: Exception
) -> Trajectory:
    return Trajectory(
        scenario_id=scenario.scenario_id,
        user_input=scenario.user_input,
        status="error",
        error=f"agent_fn raised: {exc}",
        metadata={"candidate_index": candidate_index},
    )


async def run_evaluation(
    scenarios: list[EvalScenario],
    agent_fn: AgentFn,
    judge: JudgeLike | None = None,
    *,
    k: int = 1,
    report_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    samples: int | None = None,
    timeout: float = 60.0,
    token_budget: int = 8000,
) -> EvaluationReport:
    """Run every scenario k times and aggregate a full report.

    Each candidate trajectory is scored with the injected judge. Aggregation
    produces per-scenario best/mean scores and report-level pass@k
    (capability ceiling) and pass^k (business reliability) metrics, with
    the k semantics written explicitly into the report.
    """
    samples = k if samples is None else samples
    if k <= 0 or samples < k or timeout <= 0 or token_budget <= 0:
        raise ValueError("require samples >= k > 0 and positive timeout/budget")
    if len({s.scenario_id for s in scenarios}) != len(scenarios):
        raise ValueError("scenario IDs must be unique")
    judge = judge or DEFAULT_JUDGE
    scenario_reports: list[ScenarioReport] = []
    total_tokens = 0
    total_candidates = 0
    started = datetime.now(UTC)

    for scenario in scenarios:
        results: list[EvaluationResult] = []
        trajectories = []
        for candidate_index in range(samples):
            try:
                trajectory = await asyncio.wait_for(agent_fn(scenario, candidate_index), timeout)
            except Exception as exc:
                trajectory = _fake_error_trajectory(scenario, candidate_index, exc)
            if trajectory.tokens_used < 0 or trajectory.tokens_used > token_budget:
                trajectory.error = "invalid usage or token budget exceeded"
                trajectory.status = "failed"
            trajectories.append(trajectory)
            try:
                result = await asyncio.wait_for(
                    evaluate_trajectory(
                        trajectory,
                        scenario.rubric,
                        judge=judge,
                        scenario_id=scenario.scenario_id,
                        expected_points=scenario.expected_points,
                    ),
                    timeout,
                )
            except Exception as exc:
                result = EvaluationResult(
                    scenario.scenario_id, 0.0, False, failure_reasons=[f"judge failed: {exc}"]
                )
            results.append(result)
            total_tokens += trajectory.tokens_used
            total_candidates += 1
        best = max((r.score for r in results), default=0.0)
        passed_count = sum(1 for r in results if r.passed)
        scenario_reports.append(
            ScenarioReport(
                scenario_id=scenario.scenario_id,
                scenario_name=scenario.name,
                results=results,
                best_score=best,
                mean_score=sum(r.score for r in results) / len(results) if results else 0.0,
                passed=passed_count > 0,
                pass_count=passed_count,
                trajectories=trajectories,
            )
        )

    total_scenarios = len(scenario_reports)
    passed_scenarios = sum(1 for s in scenario_reports if s.passed)
    mean_score = (
        sum(s.mean_score for s in scenario_reports) / total_scenarios if total_scenarios else 0.0
    )
    finished = datetime.now(UTC)
    return EvaluationReport(
        report_id=report_id or str(uuid4()),
        created_at=finished.isoformat(),
        scenarios=scenario_reports,
        total_scenarios=total_scenarios,
        passed_scenarios=passed_scenarios,
        average_score=round(mean_score, 4),
        pass_at_k={
            "k": k,
            "definition": "probability at least one of k candidates passes per scenario",
            "aggregate": round(
                sum(pass_at_k(samples, s.pass_count, k) for s in scenario_reports)
                / total_scenarios,
                4,
            )
            if total_scenarios
            else 0.0,
        },
        pass_hat_k={
            "k": k,
            "definition": "observed first k candidates all pass (veto reliability)",
            "aggregate": round(
                sum(all(r.passed for r in s.results[:k]) for s in scenario_reports)
                / total_scenarios,
                4,
            )
            if total_scenarios
            else 0.0,
        },
        total_tokens=total_tokens,
        duration_ms=(finished - started).total_seconds() * 1000,
        metadata={**(metadata or {}), "samples": samples, "total_candidates": total_candidates},
    )
