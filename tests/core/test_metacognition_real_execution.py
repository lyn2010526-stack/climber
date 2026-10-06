"""Scripted executor and event-stream tests; no real LLM credentials are used."""

import asyncio
from types import SimpleNamespace

import pytest

from app.core import AgentEvent, AgentEventType
from app.core.metacognition.hypothesis import HypothesisSimulator
from app.core.metacognition.real_execution import (
    LLMHypothesisVerifier,
    ModelUnavailableError,
    SubTaskExecution,
    execute_subtask_llm,
    make_engine_subtask_executor,
    parse_verdict_json,
    resolve_model_adapter,
)
from app.core.metacognition.sub_agent import SubAgentOrchestrator, SubAgentState
from app.core.principal import Principal


async def test_scripted_usage_and_capacity():
    async def execute(goal, context):
        assert context["token_budget"] > 0
        return SubTaskExecution("observed output", 7, 2, source="scripted_fake")

    pool = SubAgentOrchestrator(max_agents=1, executor=execute, token_budget=14)
    for _ in range(2):
        result = (await pool.dispatch([{"goal": "work"}]))[0]
        assert result.success
        assert result.tokens_used == 7
        assert result.source == "scripted_fake"
        assert pool.active_count == 0
        assert pool.get_agent(result.task_id).iterations == 2
    assert not (await pool.dispatch([{"goal": "work"}]))[0].success


async def test_disabled_and_unconfigured_fail(monkeypatch):
    monkeypatch.setenv("USER_METACOGNITION_REAL_EXECUTION", "false")
    pool = SubAgentOrchestrator()
    result = (await pool.dispatch([{"goal": "work"}]))[0]
    assert not result.success
    assert result.tokens_used == 0
    assert pool.get_agent(result.task_id).state == SubAgentState.FAILED
    assert pool.active_count == 0
    assert resolve_model_adapter() is None


@pytest.mark.parametrize(
    "result",
    [
        SubTaskExecution("x", 9, 1),
        SubTaskExecution("", 0, 1),
        SubTaskExecution("x", 2, 1, status="failed"),
    ],
)
async def test_invalid_executor_outcomes(result):
    async def execute(goal, context):
        return result

    pool = SubAgentOrchestrator(executor=execute, token_budget=8)
    assert not (await pool.dispatch([{"goal": "work"}]))[0].success
    assert pool.active_count == 0


async def test_timeout_and_cancel_stop_coroutine():
    started = asyncio.Event()
    stopped = asyncio.Event()

    async def blocked(goal, context):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()

    pool = SubAgentOrchestrator(executor=blocked, execution_timeout=0.01)
    assert not (await pool.dispatch([{"goal": "work"}]))[0].success
    assert stopped.is_set()
    stopped.clear()
    pool = SubAgentOrchestrator(executor=blocked)
    pending = asyncio.create_task(pool.dispatch([{"goal": "work"}]))
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    task = pool.list_agents()[0]
    assert pool.cancel_agent(task.id)
    with pytest.raises(asyncio.CancelledError):
        await pending
    assert stopped.is_set()
    assert pool.active_count == 0


async def test_model_judgment_and_experiment_are_separate():
    async def judgment(payload):
        return {"verdict": "feasible", "confidence": 0.8, "reason": "model belief"}

    async def experiment(payload):
        assert payload["context"]["principal"] == "owner"
        return {
            "success": False,
            "observed_state": {"file_exists": False},
            "evidence": ["scripted fixture observation"],
        }

    simulator = HypothesisSimulator(verifier=judgment, experiment_runner=experiment)
    verdict = await simulator.verify_hypothesis("create file")
    assert verdict["evidence_kind"] == "model_judgment"
    result = await simulator.run_experiment("create file", context={"principal": "owner"})
    assert result["evidence_kind"] == "experiment"
    assert result["status"] == "completed"
    assert result["success"] is False
    assert (await HypothesisSimulator().run_experiment("x"))["status"] == "failed"


async def test_engine_stream_adapter_preserves_owner_and_permissions():
    owner = Principal("alice", tenant_id="tenant")
    permission = object()

    class ScriptedEngine:
        def create_session(self, **options):
            assert options["user_id"] == "alice"
            return SimpleNamespace(session_id="isolated", **options)

        async def run(self, session, message):
            assert message == "work"
            from app.core.principal import get_context_principal

            assert get_context_principal() is owner
            assert session.principal is owner
            assert session.permission_config is permission
            yield AgentEvent(AgentEventType.TEXT, {"content": "actual fixture output"})
            yield AgentEvent(AgentEventType.DONE, {"tokens_used": 11})

    execute = make_engine_subtask_executor(
        ScriptedEngine(),
        principal=owner,
        permission_config=permission,
    )
    result = await execute("work", {"token_budget": 20})
    assert result.output == "actual fixture output"
    assert result.tokens_used == 11
    assert result.status == "completed"


async def test_explicit_scripted_model_adapter_and_missing_model():
    class ScriptedAdapter:
        async def chat(self, messages, tools=None, **options):
            assert tools is None
            assert messages
            assert options["max_tokens"] == 2000
            return SimpleNamespace(content="fixture output", tokens_used=13)

    output, tokens = await execute_subtask_llm("work", adapter=ScriptedAdapter())
    assert (output, tokens) == ("fixture output", 13)
    with pytest.raises(ModelUnavailableError):
        await execute_subtask_llm("work")
    with pytest.raises(ModelUnavailableError):
        await LLMHypothesisVerifier()({"goal": "work"})


async def test_failed_judgment_records_fallback_and_timeout():
    async def blocked(payload):
        await asyncio.Event().wait()

    simulator = HypothesisSimulator(verifier=blocked, verification_timeout=0.01)
    verdict = await simulator.verify_hypothesis("work")
    assert verdict["status"] == "failed"
    assert verdict["evidence_kind"] == "heuristic"

    async def malformed(payload):
        return {"verdict": "feasible", "confidence": float("nan")}

    assert (await HypothesisSimulator(verifier=malformed).verify_hypothesis("work"))[
        "status"
    ] == "failed"


@pytest.mark.parametrize("confidence", ["NaN", "Infinity", "-0.1", "1.1"])
def test_model_verdict_rejects_invalid_confidence(confidence):
    with pytest.raises(ValueError, match="confidence"):
        parse_verdict_json('{"verdict":"feasible","confidence":' + confidence + "}")


async def test_engine_stream_is_closed_on_budget_and_cancellation():
    closed = asyncio.Event()
    started = asyncio.Event()

    class ScriptedEngine:
        def create_session(self, **options):
            return SimpleNamespace(
                session_id="isolated", _run_tokens=0, stop=lambda: None, **options
            )

        async def run(self, session, message):
            try:
                started.set()
                if message == "costly":
                    session._run_tokens = 9
                    yield AgentEvent(AgentEventType.TEXT, {"content": "fixture"})
                await asyncio.Event().wait()
            finally:
                closed.set()

    execute = make_engine_subtask_executor(ScriptedEngine(), principal=Principal("alice"))
    result = await execute("costly", {"token_budget": 8})
    assert result.status == "failed"
    assert result.tokens_used == 9
    assert closed.is_set()
    closed.clear()
    started.clear()
    pending = asyncio.create_task(execute("blocked", {}))
    await started.wait()
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    assert closed.is_set()
