"""Verify the metacognition orchestrator wiring in the AgentEngine main loop."""

from __future__ import annotations

import pytest

from app.core.session import AgentSession


def _minimal_engine(metacognition):
    from app.core.agent_engine import AgentEngine
    from app.core.tool_prioritizer import ToolPrioritizer

    engine = AgentEngine.__new__(AgentEngine)
    engine._metacognition = metacognition
    engine.permission_timeout_seconds = 30.0
    engine.tool_prioritizer = ToolPrioritizer()
    engine.debug_loop = None
    return engine


def _patch_engine_side_effects(monkeypatch: pytest.MonkeyPatch, engine) -> None:
    import app.core.agent_engine as engine_module

    async def _persist(*args, **kwargs):
        return None

    async def _save_checkpoint(session, channels, **kwargs):
        return None

    async def _debug(session, tr):
        return None

    monkeypatch.setattr(engine_module, "persist_message", _persist)
    monkeypatch.setattr(engine, "_save_checkpoint", _save_checkpoint)
    monkeypatch.setattr(engine, "_handle_tool_debug", _debug)
    engine._validate_tool_call = lambda session, tool_name, arguments: (True, "")


async def test_engine_metacognition_property_fail_open() -> None:
    from app.core.agent_engine import AgentEngine

    engine = AgentEngine.__new__(AgentEngine)
    engine._metacognition = None

    orchestrator = engine.metacognition
    assert orchestrator is not None
    assert engine.metacognition_enabled is True
    assert engine._metacognition is not None


async def test_engine_metacognition_property_built_once() -> None:
    from app.core.agent_engine import AgentEngine

    engine = AgentEngine.__new__(AgentEngine)
    engine._metacognition = None

    first = engine.metacognition
    second = engine.metacognition
    assert first is second


def test_metacognition_orchestrator_guidance_contract() -> None:
    from app.core.metacognition import ExecutionContext, MetacognitionOrchestrator

    orchestrator = MetacognitionOrchestrator(token_budget=8000)
    orchestrator.initialize(
        ExecutionContext(goal="solve the puzzle", available_tools=["web_search", "calculator"])
    )

    guidance = orchestrator.pre_action(iteration=1)
    assert guidance["proceed"] in (True, False)
    assert "should_stop" in guidance
    assert "should_compress" in guidance
    assert isinstance(guidance["warnings"], list)

    feedback = orchestrator.post_action(
        iteration=1,
        tool_name="calculator",
        arguments={"expr": "2+2"},
        result="4",
        tokens_used=0,
        success=True,
    )
    assert "continue" in feedback
    assert "health_score" in feedback


class _ControlledMetacognition:
    def __init__(self, proceed: bool = True, post_results: list[dict] | None = None) -> None:
        self._proceed = proceed
        self._post_results = post_results or []
        self.pre_calls: list[int] = []
        self.post_calls: list[tuple] = []

    def initialize(self, ctx):
        return None

    def pre_action(self, iteration: int) -> dict:
        self.pre_calls.append(iteration)
        return {
            "proceed": self._proceed,
            "should_stop": not self._proceed,
            "should_compress": False,
            "warnings": [],
        }

    def post_action(self, *args, **kwargs) -> dict:
        self.post_calls.append(args)
        return (self._post_results or [{}]).pop(0)


def _chat_result(tool_call_id: str = "call_1") -> _ChatResult:
    return _ChatResult([{"id": tool_call_id, "type": "function", "function": {"name": "calculator", "arguments": {}}}])


class _ChatResult:
    def __init__(self, tool_calls: list[dict]) -> None:
        self.tool_calls = tool_calls
        self.content = ""
        self.tokens_used = 0


class _ToolResult:
    def __init__(self, tool_call_id: str, tool_name: str, result: str) -> None:
        self.tool_call_id = tool_call_id
        self.tool_name = tool_name
        self.result = result
        self.error = ""
        self.success = True
        self.duration_ms = 1
        self.arguments = {}


async def test_handle_tool_execution_blocks_when_metacognition_says_stop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.agent_engine import AgentEventType

    meta = _ControlledMetacognition(proceed=False)
    engine = _minimal_engine(meta)
    _patch_engine_side_effects(monkeypatch, engine)
    session = AgentSession(session_id="wire-block", agent_id="agent", user_id="user", api_key="k", model_id="m")

    ran_tools: list[str] = []

    class _Executor:
        async def execute_all(self, calls):
            ran_tools.append("executed")
            return []

    events = [
        ev
        async for ev in engine._handle_tool_execution(
            session=session,
            executor=_Executor(),
            result=_chat_result(),
            iteration=1,
            ctx_tokens=10,
            metacognition=meta,
        )
    ]
    assert meta.pre_calls == [1]
    assert ran_tools == []
    assert any(ev.type == AgentEventType.TOOL_RESULT and ev.data.get("error") == "resource_stop" for ev in events)
    checkpoint = next(ev for ev in events if ev.type == AgentEventType.CHECKPOINT)
    assert checkpoint.data["metacognition"]["proceed"] is False


async def test_handle_tool_execution_feeds_post_action_back_to_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.agent_engine import AgentEventType

    meta = _ControlledMetacognition(proceed=True, post_results=[{"continue": True, "health_score": 0.9}])
    engine = _minimal_engine(meta)
    _patch_engine_side_effects(monkeypatch, engine)
    session = AgentSession(session_id="wire-feedback", agent_id="agent", user_id="user", api_key="k", model_id="m")

    class _Executor:
        async def execute_all(self, calls):
            return [_ToolResult("call_1", "calculator", "4")]

    events = [
        ev
        async for ev in engine._handle_tool_execution(
            session=session,
            executor=_Executor(),
            result=_chat_result(),
            iteration=2,
            ctx_tokens=10,
            metacognition=meta,
        )
    ]
    assert meta.pre_calls == [2]
    assert len(meta.post_calls) == 1
    event = next(ev for ev in events if ev.type == AgentEventType.CHECKPOINT)
    assert event.data["metacognition"]["feedback"][0]["health_score"] == 0.9