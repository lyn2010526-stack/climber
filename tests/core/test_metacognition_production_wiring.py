"""Production bootstrap/hook contracts over scripted events, with no network model."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.core import AgentEvent, AgentEventType, ChatResult
from app.core.agent_engine import AgentEngine
from app.core.engine.bootstrap import init_debug_loop
from app.core.principal import Principal, get_context_principal
from app.core.resilience import TimeoutConfig
from app.core.session import AgentSession


class ScriptedProductionEngine(AgentEngine):
    """Use the production bootstrap and facade properties with deterministic events."""

    def __init__(self):
        self._metacognition = None
        self.children = []
        self.metas = []
        self.model_registry = SimpleNamespace(get_or_create=self.adapter)
        init_debug_loop(self)

    @staticmethod
    def adapter(**options):
        assert options["api_key"] == "user-fixture-key"

        async def chat(**options):
            return SimpleNamespace(
                content='{"verdict":"feasible","confidence":0.7,"reason":"fixture"}',
                tokens_used=2,
            )

        return SimpleNamespace(chat=chat)

    def create_session(self, **options):
        session = AgentSession(session_id=str(len(self.children)), **options)
        self.children.append(session)
        return session

    async def run(self, session, message):
        session.messages = [{"role": "user", "content": message}]
        async for event in self._iteration_loop(session, None, None):
            yield event

    async def _iteration_loop(self, session, executor, compressor):
        del executor, compressor
        meta = self.metacognition if self.metacognition_enabled else None
        if getattr(session, "metacognition_disabled", False):
            assert meta is None
            assert get_context_principal() == session.principal
            yield AgentEvent(AgentEventType.TEXT, {"content": "observed fixture"})
            yield AgentEvent(AgentEventType.DONE, {"tokens_used": 7, "status": "completed"})
            return
        self.metas.append(meta)
        from app.core.metacognition import ExecutionContext

        meta.initialize(ExecutionContext("work", [], token_budget=20))
        yield AgentEvent(AgentEventType.DONE, {"meta": meta})


def parent(key="user-fixture-key", user="alice"):
    session = AgentSession(
        session_id="parent",
        agent_id="agent",
        user_id=user,
        provider="scripted",
        model_id="fixture",
        api_key=key,
    )
    session.principal = Principal("alice", tenant_id="tenant")
    return session


async def test_bootstrap_hook_injects_execution_experiment_and_judgment():
    engine = ScriptedProductionEngine()
    session = parent()
    events = [event async for event in engine.run(session, "work")]
    meta = events[-1].data["meta"]
    result = (await meta.dispatch_subtasks([{"goal": "work"}]))[0]
    assert result.success
    assert result.tokens_used == 7
    child = engine.children[0]
    assert child.principal is session.principal
    assert child.permission_config is session.permission_config
    assert child.max_iterations <= 5
    judgment = await meta._simulator.verify_hypothesis("work")
    assert judgment["evidence_kind"] == "model_judgment"
    experiment = await meta.run_experiment(
        "work",
        context={
            "rubric": [
                {
                    "item_id": "observed",
                    "description": "observed output",
                    "contains_any": ["observed fixture"],
                    "essential": True,
                }
            ],
        },
    )
    assert experiment["success"]
    assert experiment["evidence_kind"] == "experiment"
    assert experiment["observed_state"]["tokens_used"] == 7
    assert len(engine.children) == 2
    missing = await meta.run_experiment("work")
    assert missing["status"] == "failed"
    assert "unconfigured" in missing["reason"]


@pytest.mark.parametrize(("key", "user"), [("", "alice"), ("user-fixture-key", "other")])
async def test_bootstrap_missing_credentials_or_owner_fails_closed(key, user):
    engine = ScriptedProductionEngine()
    events = [event async for event in engine.run(parent(key, user), "work")]
    meta = events[-1].data["meta"]
    result = (await meta.dispatch_subtasks([{"goal": "work"}]))[0]
    assert not result.success
    assert "unconfigured" in result.result
    estimate = await meta._simulator.verify_hypothesis("work")
    assert estimate["evidence_kind"] == "heuristic"
    assert estimate["status"] == "failed"
    assert not engine.children


async def test_real_iteration_loop_bootstrap_reaches_injected_child():
    class MainLoopEngine(ScriptedProductionEngine):
        async def run(self, session, message):
            from app.core.compressor import ContextCompressor
            from app.core.task_state_machine import TaskState

            session.messages = [{"role": "user", "content": message}]
            await session.state_machine.transition(TaskState.PROCESSING)
            async for event in self._iteration_loop(
                session, None, ContextCompressor(session.context_config)
            ):
                yield event
            yield AgentEvent(AgentEventType.DONE, {"tokens_used": 7, "status": "completed"})

        async def _iteration_loop(self, session, executor, compressor):
            from app.core.engine.runner import iteration_loop

            async for event in iteration_loop(self, session, executor, compressor):
                yield event

    engine = MainLoopEngine()
    engine._build_tools_for_session = Mock(return_value=[])
    engine._call_llm_with_resilience = AsyncMock(
        return_value=ChatResult(content="observed fixture", finish_reason="stop", tokens_used=7)
    )
    engine._save_checkpoint = AsyncMock()
    engine._send_completion_notification = Mock()
    engine._run_store = SimpleNamespace(record_response=AsyncMock())

    def adapter(**options):
        del options
        return SimpleNamespace(capabilities=SimpleNamespace(streaming=False, max_tokens=100000))

    engine.model_registry = SimpleNamespace(get_or_create=adapter)

    async def text(session, result, adapter):
        del session, adapter
        yield AgentEvent(AgentEventType.TEXT, {"content": result.content})

    engine._handle_text_result = text
    session = parent()
    session.messages = [{"role": "user", "content": "work"}]
    from app.core.compressor import ContextCompressor
    from app.core.task_state_machine import TaskState

    await session.state_machine.transition(TaskState.PROCESSING)
    events = [
        event
        async for event in engine._iteration_loop(
            session, None, ContextCompressor(session.context_config)
        )
    ]
    assert events
    meta = session.metacognition_orchestrator
    assert meta.get_state().simulation is not None
    result = (await meta.dispatch_subtasks([{"goal": "work"}]))[0]
    assert result.success
    assert len(engine.children) == 1
    assert engine.children[0].metacognition_disabled
    assert not hasattr(engine.children[0], "metacognition_orchestrator")


async def test_unavailable_model_and_parent_timeout():
    engine = ScriptedProductionEngine()

    def unavailable(**options):
        del options
        raise RuntimeError("fixture provider unavailable")

    engine.model_registry = SimpleNamespace(get_or_create=unavailable)
    events = [event async for event in engine.run(parent(), "work")]
    result = (await events[-1].data["meta"].dispatch_subtasks([{"goal": "work"}]))[0]
    assert not result.success
    assert "unconfigured" in result.result

    engine = ScriptedProductionEngine()
    session = parent()
    session.session_config.timeouts = TimeoutConfig(per_call_seconds=0.01)
    events = [event async for event in engine.run(session, "work")]
    closed = asyncio.Event()

    async def blocked(session, message):
        del session, message
        try:
            await asyncio.Event().wait()
            yield AgentEvent(AgentEventType.DONE, {})
        finally:
            closed.set()

    engine.run = blocked
    result = (await events[-1].data["meta"].dispatch_subtasks([{"goal": "work"}]))[0]
    assert not result.success
    assert closed.is_set()


async def test_bootstrap_session_isolation_and_parent_budget():
    engine = ScriptedProductionEngine()
    first = parent()
    second = parent()
    a = [event async for event in engine.run(first, "work")]
    b = [event async for event in engine.run(second, "work")]
    assert a[-1].data["meta"] is not b[-1].data["meta"]
    first._run_tokens = first.context_config.max_tokens
    result = (await a[-1].data["meta"].dispatch_subtasks([{"goal": "work"}]))[0]
    assert not result.success
    assert not engine.children


async def test_bootstrap_execution_limit_and_budget_shared_with_model_judgment():
    engine = ScriptedProductionEngine()
    session = parent()
    events = [event async for event in engine.run(session, "work")]
    meta = events[-1].data["meta"]
    for _ in range(5):
        assert (await meta.dispatch_subtasks([{"goal": "work"}]))[0].success
    result = (await meta.dispatch_subtasks([{"goal": "work"}]))[0]
    assert not result.success
    assert "limit exceeded" in result.result
    assert len(engine.children) == 5

    session = parent()
    session.context_config.max_tokens = 2
    events = [event async for event in engine.run(session, "work")]
    meta = events[-1].data["meta"]
    assert (await meta._simulator.verify_hypothesis("work"))["status"] == "completed"
    result = (await meta.dispatch_subtasks([{"goal": "work"}]))[0]
    assert not result.success
    assert "budget exhausted" in result.result


async def test_concurrent_main_loop_scopes_and_explicit_failed_rubric():
    engine = ScriptedProductionEngine()
    first, second = parent(), parent()

    async def collect(session):
        return [event async for event in engine.run(session, "work")]

    a, b = await asyncio.gather(collect(first), collect(second))
    assert a[-1].data["meta"] is first.metacognition_orchestrator
    assert b[-1].data["meta"] is second.metacognition_orchestrator
    assert first.metacognition_orchestrator is not second.metacognition_orchestrator
    result = await first.metacognition_orchestrator.run_experiment(
        "work",
        context={
            "rubric": [
                {
                    "item_id": "required",
                    "description": "required observation",
                    "contains_any": ["absent fixture"],
                    "essential": True,
                }
            ],
        },
    )
    assert result["status"] == "completed"
    assert result["success"] is False
