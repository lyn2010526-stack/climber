"""Session-owned production wiring; credentials come solely from the parent session."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from types import SimpleNamespace
from typing import Any, cast

from app.core.evaluation.judges import DeterministicJudge
from app.core.evaluation.models import RubricItem, Trajectory
from app.core.metacognition.orchestrator import MetacognitionOrchestrator
from app.core.metacognition.real_execution import (
    LLMHypothesisVerifier,
    SubTaskExecution,
    make_engine_subtask_executor,
)


class _ChildEngine:
    """Retain the engine permission chain while disabling recursive meta execution."""

    def __init__(self, engine: Any, parent: Any):
        self.engine = engine
        self.parent = parent

    def create_session(self, **options: Any) -> Any:
        child = self.engine.create_session(
            **options,
            tools=list(self.parent.tools),
            context_config=deepcopy(self.parent.context_config),
            mode=self.parent.mode,
        )
        child.metacognition_disabled = True
        child.max_iterations = min(self.parent.max_iterations, 5)
        return child

    def run(self, session: Any, message: str) -> Any:
        return self.engine.run(session, message)


def build_session_orchestrator(engine: Any, session: Any) -> MetacognitionOrchestrator:
    """Fail closed on absent identity/model configuration; never resolve ambient keys."""
    from app.core.principal import (
        get_context_principal,
        reset_current_principal,
        set_current_principal,
    )

    budget = max(1, int(session.context_config.max_tokens))
    owner = getattr(session, "principal", None)
    if owner is None:
        try:
            owner = get_context_principal()
        except RuntimeError:
            owner = None
    timeout = 60.0
    timeouts = getattr(session.session_config, "timeouts", None)
    if timeouts is not None:
        timeout = min(timeout, timeouts.per_session_seconds, timeouts.per_call_seconds)
    configured = bool(
        owner is not None
        and owner.subject_id == session.user_id
        and session.api_key
        and session.provider
        and session.model_id
        and getattr(session, "permission_config", None) is not None
    )
    adapter = None
    reason = "unconfigured: session model credentials, principal or permissions unavailable"
    if configured:
        try:
            adapter = engine.model_registry.get_or_create(
                provider=session.provider,
                model_id=session.model_id,
                api_key=session.api_key,
                base_url=session.base_url,
            )
        except Exception as exc:
            reason = f"unconfigured: model unavailable ({type(exc).__name__})"

    async def unavailable(goal: str, context: dict[str, Any] | None) -> SubTaskExecution:
        del goal, context
        raise RuntimeError(reason)

    executor = unavailable
    if adapter is not None:
        execute = make_engine_subtask_executor(
            _ChildEngine(engine, session),
            principal=owner,
            permission_config=session.permission_config,
            provider=session.provider,
            model_id=session.model_id,
            api_key=session.api_key,
            base_url=session.base_url,
            system_prompt=session.system_prompt,
        )

        lock = asyncio.Lock()
        spent = 0
        executions = 0

        async def judgment_chat(**options: Any) -> Any:
            nonlocal spent
            async with lock:
                remaining = budget - spent - getattr(session, "_run_tokens", 0)
                if getattr(session, "_stop_requested", False) or remaining <= 0:
                    raise RuntimeError("parent stopped or token budget exhausted")
                options["max_tokens"] = min(options.get("max_tokens", remaining), remaining)
                assert owner is not None
                principal_token = set_current_principal(owner)
                try:
                    response = await adapter.chat(**options)
                except BaseException:
                    spent += remaining
                    raise
                finally:
                    reset_current_principal(principal_token)
                usage = response.tokens_used
                if type(usage) is not int or usage < 0:
                    spent += remaining
                    raise ValueError("model returned invalid usage")
                spent += usage
                if usage > remaining:
                    raise ValueError("model judgment token budget exceeded")
                return response

        async def bounded(goal: str, context: dict[str, Any] | None) -> SubTaskExecution:
            nonlocal spent, executions
            async with lock:
                remaining = budget - spent - getattr(session, "_run_tokens", 0)
                remaining = min(remaining, (context or {}).get("token_budget", remaining))
                if getattr(session, "_stop_requested", False) or remaining <= 0:
                    raise RuntimeError("parent stopped or token budget exhausted")
                if executions >= 5:
                    raise RuntimeError("session subtask execution limit exceeded")
                executions += 1
                try:
                    result = await asyncio.wait_for(
                        execute(goal, {**(context or {}), "token_budget": remaining}), timeout
                    )
                except BaseException:
                    spent += remaining
                    raise
                spent += result.tokens_used
                return result

        executor = bounded
        verifier_adapter = SimpleNamespace(chat=judgment_chat)
    else:
        verifier_adapter = None

    orchestrator = MetacognitionOrchestrator(
        token_budget=budget,
        verifier=LLMHypothesisVerifier(adapter=verifier_adapter, timeout=timeout),
        sub_agent_executor=executor,
    )

    async def experiment(payload: dict[str, Any]) -> dict[str, Any]:
        context = payload.get("context") or {}
        rubric_data = context.get("rubric")
        if not rubric_data:
            raise RuntimeError("unconfigured: experiment requires an explicit observable rubric")
        rubric = [
            item if isinstance(item, RubricItem) else RubricItem(**item) for item in rubric_data
        ]
        goal = cast("str", payload.get("goal") or payload.get("hypothesis"))
        result = (await orchestrator.dispatch_subtasks([{"goal": goal, "context": context}]))[0]
        if not result.success:
            raise RuntimeError(result.result)
        trajectory = Trajectory(
            "experiment", goal, output=result.result, tokens_used=result.tokens_used
        )
        judgment = DeterministicJudge().judge(trajectory, rubric)
        return {
            "success": judgment.passed,
            "observed_state": {"output": result.result, "tokens_used": result.tokens_used},
            "evidence": [verdict.reason for verdict in judgment.verdicts],
            "evaluation": judgment.to_dict(),
        }

    orchestrator.configure_experiment_runner(experiment)
    return orchestrator
