"""Regression tests for R11-N06: workflow LLM sampling parameters.

``build_workflow_from_graph`` stores ``temperature`` / ``max_tokens`` on the
LLM node config, but ``WorkflowEngine._execute_llm_node`` previously dropped
them, so the values never reached the model adapter. These tests lock the
full path: node config -> create_session -> per-session sampling overrides ->
adapter call kwargs.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.core import AgentEvent, AgentEventType
from app.core.engine.llm_calls import call_llm, sampling_kwargs, stream_chat
from app.workflow import NodeType, WorkflowNode


class _FakeSession:
    pass


class _RecordingEngine:
    """Stand-in for AgentEngine; records create_session kwargs."""

    def __init__(self, *args: Any, **kwargs: Any):
        self.session_kwargs: list[dict[str, Any]] = []

    def create_session(self, **kwargs: Any) -> _FakeSession:
        self.session_kwargs.append(kwargs)
        return _FakeSession()

    async def run(self, session: _FakeSession, message: str):
        yield AgentEvent(type=AgentEventType.TEXT, data={"content": "ok"})


class _RecordingAdapter:
    """Captures kwargs passed to chat/stream_chat."""

    def __init__(self) -> None:
        self.chat_kwargs: dict[str, Any] | None = None
        self.stream_kwargs: dict[str, Any] | None = None

    async def chat(self, messages: list[dict[str, Any]], tools: Any = None, **kwargs: Any):
        from app.core import ChatResult

        self.chat_kwargs = kwargs
        return ChatResult(content="done", finish_reason="stop")

    async def stream_chat(self, messages: list[dict[str, Any]], tools: Any = None, **kwargs: Any):
        from app.core import ChatResult

        self.stream_kwargs = kwargs
        yield ChatResult(content="chunk", finish_reason="stop")


def _agent_session(**overrides: Any):
    from app.core.session import AgentSession

    base = dict(user_id="u", provider="openai", model_id="m", api_key="k")
    base.update(overrides)
    return AgentSession(**base)


def test_build_graph_stores_sampling_params() -> None:
    from app.core.workflow_executor import build_workflow_from_graph

    workflow = build_workflow_from_graph(
        nodes=[
            {"id": "in", "type": "input", "data": {}},
            {
                "id": "llm1",
                "type": "llm",
                "data": {
                    "model": "gpt-4",
                    "prompt": "say hi",
                    "temperature": "0.3",
                    "max_tokens": "512",
                },
            },
            {"id": "out", "type": "output", "data": {}},
        ],
        edges=[{"source": "in", "target": "llm1"}, {"source": "llm1", "target": "out"}],
    )
    llm_node = next(n for n in workflow.nodes if n.id == "llm1")
    assert llm_node.config["temperature"] == 0.3
    assert llm_node.config["max_tokens"] == 512


async def test_execute_llm_node_passes_sampling_params_to_create_session() -> None:
    from app.workflow.engine import WorkflowEngine

    engine = _RecordingEngine()
    workflow_engine = WorkflowEngine(engine=engine)  # type: ignore[arg-type]
    node = WorkflowNode(
        id="n1",
        type=NodeType.LLM,
        name="llm",
        config={
            "model_id": "gpt-4",
            "prompt": "hello",
            "temperature": 0.3,
            "max_tokens": 512,
        },
    )

    result = await workflow_engine._execute_llm_node(node, {}, "user-1")

    assert result["response"] == "ok"
    assert engine.session_kwargs, "create_session was not called"
    kwargs = engine.session_kwargs[0]
    assert kwargs["temperature"] == 0.3
    assert kwargs["max_tokens"] == 512


async def test_execute_llm_node_omits_sampling_params_when_unset() -> None:
    from app.workflow.engine import WorkflowEngine

    engine = _RecordingEngine()
    workflow_engine = WorkflowEngine(engine=engine)  # type: ignore[arg-type]
    node = WorkflowNode(
        id="n1",
        type=NodeType.LLM,
        name="llm",
        config={"model_id": "gpt-4", "prompt": "hello"},
    )

    await workflow_engine._execute_llm_node(node, {}, "user-1")

    kwargs = engine.session_kwargs[0]
    # Unset params must stay None so provider defaults apply downstream.
    assert kwargs["temperature"] is None
    assert kwargs["max_tokens"] is None


def test_sampling_kwargs_defaults_to_empty() -> None:
    assert sampling_kwargs(_agent_session()) == {}


def test_sampling_kwargs_forwards_session_overrides() -> None:
    session = _agent_session(temperature=0.3, max_tokens=512)
    assert sampling_kwargs(session) == {"temperature": 0.3, "max_tokens": 512}


async def test_stream_chat_forwards_sampling_kwargs() -> None:
    adapter = _RecordingAdapter()
    session = _agent_session(temperature=0.1, max_tokens=64)

    result = await stream_chat(adapter, session, [])

    assert result is not None
    assert adapter.stream_kwargs == {"temperature": 0.1, "max_tokens": 64}


async def test_call_llm_forwards_sampling_kwargs() -> None:
    adapter = _RecordingAdapter()
    session = _agent_session(temperature=0.9, max_tokens=128)

    result = await call_llm(adapter, session, [])

    assert result is not None
    assert adapter.chat_kwargs == {"temperature": 0.9, "max_tokens": 128}


async def test_session_sampling_survives_snapshot_round_trip() -> None:
    session = _agent_session(temperature=0.25, max_tokens=256)

    restored = type(session).from_snapshot(session.snapshot(), api_key="k")

    assert restored.temperature == 0.25
    assert restored.max_tokens == 256
    assert sampling_kwargs(restored) == {"temperature": 0.25, "max_tokens": 256}
