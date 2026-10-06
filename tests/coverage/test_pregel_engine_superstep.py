"""Coverage tests for app.core.engine.pregel.engine."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.core.engine.pregel.checkpoint import Checkpoint, CheckpointConfig, InMemoryCheckpointSaver
from app.core.engine.pregel.command import Command
from app.core.engine.pregel.engine import (
    PregelEngine,
    _drop_terminals,
)
from app.core.engine.pregel.graph import StateGraph
from app.core.engine.pregel.policies import DefaultErrorHandler, RetryPolicy, TimeoutPolicy
from app.core.engine.pregel.state import GraphState


def _linear_graph(interrupt_before=None, interrupt_after=None, **compile_kwargs):
    g = StateGraph()

    async def a(state: dict[str, Any]) -> dict[str, Any]:
        return {"x": state.get("x", 0) + 1}

    async def b(state: dict[str, Any]) -> dict[str, Any]:
        return {"done": True}

    g.add_node("a", a)
    g.add_node("b", b)
    g.add_edge("a", "b")
    g.set_entry_point("a")
    return g.compile(
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
        **compile_kwargs,
    )


def test_drop_terminals() -> None:
    assert _drop_terminals(["a", "__end__", "END", "b"]) == ["a", "b"]


async def test_run_linear_graph() -> None:
    compiled = _linear_graph()
    result = await compiled.invoke({"x": 1})
    assert result["x"] == 2
    assert result["done"] is True


async def test_run_generates_thread_id_when_missing() -> None:
    compiled = _linear_graph()
    result = await compiled.invoke({}, config={})
    assert result["done"] is True


async def test_command_update_and_goto() -> None:
    g = StateGraph()

    def a(state: dict[str, Any]) -> Command:
        return Command(update={"y": 5}, goto="b")

    def b(state: dict[str, Any]) -> dict[str, Any]:
        return {"y_doubled": state["y"] * 2}

    g.add_node("a", a)
    g.add_node("b", b)
    g.set_entry_point("a")
    compiled = g.compile()
    result = await compiled.invoke({})
    assert result["y"] == 5
    assert result["y_doubled"] == 10


async def test_goto_resume_value_injected() -> None:
    g = StateGraph()

    def a(state: dict[str, Any]) -> Command:
        return Command(goto="__end__", resume="human-value")

    g.add_node("a", a)
    g.set_entry_point("a")
    compiled = g.compile()
    result = await compiled.invoke({})
    assert result["__resume_value__"] == "human-value"


async def test_conditional_edges_with_path_map() -> None:
    g = StateGraph()

    def a(state: dict[str, Any]) -> dict[str, Any]:
        return {"route": state.get("route")}

    def b(state: dict[str, Any]) -> dict[str, Any]:
        return {"hit": "b"}

    def c(state: dict[str, Any]) -> dict[str, Any]:
        return {"hit": "c"}

    g.add_node("a", a)
    g.add_node("b", b)
    g.add_node("c", c)
    g.add_conditional_edges(
        "a",
        lambda s: s.get("route"),
        {"go_b": "b", "go_c": "c"},
    )
    g.set_entry_point("a")
    compiled = g.compile()

    assert (await compiled.invoke({"route": "go_b"}))["hit"] == "b"
    assert (await compiled.invoke({"route": "go_c"}))["hit"] == "c"


async def test_conditional_edges_without_path_map() -> None:
    g = StateGraph()

    def a(state: dict[str, Any]) -> dict[str, Any]:
        return {}

    def b(state: dict[str, Any]) -> dict[str, Any]:
        return {"hit": "b"}

    g.add_node("a", a)
    g.add_node("b", b)
    g.add_conditional_edges("a", lambda s: "b")
    g.set_entry_point("a")
    result = await g.compile().invoke({})
    assert result["hit"] == "b"


async def test_conditional_entry_point() -> None:
    g = StateGraph()

    def a(state: dict[str, Any]) -> dict[str, Any]:
        return {"hit": "a"}

    async def router(state: dict[str, Any]) -> str:
        return "a"

    g.add_node("a", a)
    g.set_conditional_entry_point(router)
    result = await g.compile().invoke({})
    assert result["hit"] == "a"


async def test_router_none_and_exception_via_route_next() -> None:
    engine = PregelEngine(StateGraph())
    assert await engine._resolve_router(lambda s: None, GraphState()) == "__end__"

    def boom(state: Any) -> str:
        raise RuntimeError("router-fail")

    assert await engine._resolve_router(boom, GraphState()) == "__end__"

    async def async_router(state: Any) -> str:
        return "node"

    assert await engine._resolve_router(async_router, GraphState()) == "node"


async def test_route_next_goto_variants() -> None:
    g = StateGraph()
    g.add_node("a", lambda s: {})
    g.add_node("b", lambda s: {})
    engine = PregelEngine(g)

    assert await engine._route_next("a", "b", GraphState()) == ["b"]
    assert await engine._route_next("a", "__end__", GraphState()) == ["__end__"]
    assert await engine._route_next("a", "ghost", GraphState()) == []
    assert await engine._route_next("a", ["b", "ghost", "__end__"], GraphState()) == [
        "b",
        "__end__",
    ]


async def test_route_next_conditional_invalid_targets() -> None:
    g = StateGraph()
    g.add_node("a", lambda s: {})
    g.add_conditional_edges("a", lambda s: "ghost")
    engine = PregelEngine(g)
    assert await engine._route_next("a", None, GraphState()) == []

    g2 = StateGraph()
    g2.add_node("a", lambda s: {})
    g2.add_conditional_edges("a", lambda s: "__end__")
    engine2 = PregelEngine(g2)
    assert await engine2._route_next("a", None, GraphState()) == []


async def test_interrupt_before_and_resume() -> None:
    compiled = _linear_graph(interrupt_before=["b"])
    state = await compiled.invoke({"x": 1}, config={"thread_id": "t-int"})
    assert state["__interrupted__"] is True
    assert state["__interrupt_node__"] == "b"
    assert "done" not in state

    resumed = await compiled.resume_with({"thread_id": "t-int"}, "approved")
    assert resumed["done"] is True


async def test_interrupt_after_wraps_dict_and_command() -> None:
    g = StateGraph()

    async def a(state: dict[str, Any]) -> dict[str, Any]:
        return {"x": 1}

    async def b(state: dict[str, Any]) -> Command:
        return Command(update={"y": 2})

    g.add_node("a", a)
    g.add_node("b", b)
    g.add_edge("a", "b")
    g.set_entry_point("a")
    compiled = g.compile(interrupt_after=["a", "b"])
    state = await compiled.invoke({}, config={"thread_id": "t-after"})
    assert state["__interrupted__"] is True
    # interrupt fired after "a" so "b" never ran
    assert "y" not in state


async def test_command_interrupt_metadata_marks_interrupt() -> None:
    g = StateGraph()

    def a(state: dict[str, Any]) -> Command:
        return Command(update={"x": 1}, metadata={"interrupt": True})

    g.add_node("a", a)
    g.set_entry_point("a")
    state = await g.compile().invoke({}, config={"thread_id": "t-cmd"})
    assert state["__interrupted__"] is True
    assert state["__interrupt_node__"] == "a"


async def test_resume_nodes_config_selects_active_nodes() -> None:
    g = StateGraph()

    def a(state: dict[str, Any]) -> dict[str, Any]:
        return {"hit": "a"}

    def b(state: dict[str, Any]) -> dict[str, Any]:
        return {"hit": "b"}

    g.add_node("a", a)
    g.add_node("b", b)
    g.set_entry_point("a")
    compiled = g.compile()
    result = await compiled.invoke({}, config={"thread_id": "t-rn", "__resume_nodes__": ["b"]})
    assert result["hit"] == "b"


async def test_restore_from_checkpoint_with_pending_nodes() -> None:
    g = StateGraph()

    def b(state: dict[str, Any]) -> dict[str, Any]:
        return {"done": True, "seed": state.get("seed")}

    g.add_node("b", b)
    g.add_edge("b", "__end__")
    g.set_entry_point("b")
    saver = InMemoryCheckpointSaver()
    engine = PregelEngine(g, checkpointer=saver)
    cfg = CheckpointConfig(thread_id="t-restore")
    await saver.put(cfg, Checkpoint(values={"seed": 7}, next_nodes=["b"], step=1))

    result = await engine.run(GraphState(), config={"thread_id": "t-restore"})
    assert result["done"] is True
    assert result["seed"] == 7


async def test_restore_interrupt_marker_does_not_replay_entry() -> None:
    g = StateGraph()

    def a(state: dict[str, Any]) -> dict[str, Any]:
        return {"hit": "a"}

    g.add_node("a", a)
    g.set_entry_point("a")
    saver = InMemoryCheckpointSaver()
    engine = PregelEngine(g, checkpointer=saver)
    cfg = CheckpointConfig(thread_id="t-marker")
    await saver.put(
        cfg,
        Checkpoint(values={"__interrupt_node__": "a"}, next_nodes=[], step=3),
    )
    result = await engine.run(GraphState(), config={"thread_id": "t-marker"})
    assert "hit" not in result


async def test_max_steps_limits_self_loop() -> None:
    g = StateGraph()

    def a(state: dict[str, Any]) -> dict[str, Any]:
        return {"count": state.get("count", 0) + 1}

    g.add_node("a", a)
    g.add_edge("a", "a")
    g.set_entry_point("a")
    result = await g.compile().invoke({}, config={"max_steps": 3})
    assert result["count"] == 3


async def test_run_timeout_default_handler_continues() -> None:
    g = StateGraph()

    async def slow(state: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0.2)
        return {"done": True}

    g.add_node("slow", slow)
    g.set_entry_point("slow")
    compiled = g.compile(timeout_policy=TimeoutPolicy(run_timeout=0.01))
    result = await compiled.invoke({})
    assert result.get("__error__") is True


async def test_run_timeout_strict_handler_reraises() -> None:
    g = StateGraph()

    async def slow(state: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0.2)
        return {"done": True}

    g.add_node("slow", slow)
    g.set_entry_point("slow")
    compiled = g.compile(
        timeout_policy=TimeoutPolicy(run_timeout=0.01),
        error_handler=DefaultErrorHandler(continue_on_error=False),
    )
    with pytest.raises(TimeoutError):
        await compiled.invoke({})


async def test_node_timeout_policy_marks_error() -> None:
    g = StateGraph()

    async def slow(state: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0.2)
        return {"done": True}

    g.add_node("slow", slow)
    g.set_entry_point("slow")
    compiled = g.compile(
        timeout_policy=TimeoutPolicy(node_timeout=0.01),
        retry_policy=RetryPolicy(max_attempts=1),
    )
    result = await compiled.invoke({})
    assert result.get("__error__") is True


async def test_node_error_strict_handler_raises() -> None:
    g = StateGraph()

    def boom(state: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("node-boom")

    g.add_node("boom", boom)
    g.set_entry_point("boom")
    compiled = g.compile(
        error_handler=DefaultErrorHandler(continue_on_error=False),
        retry_policy=RetryPolicy(max_attempts=1, initial_interval=0.0, jitter=False),
    )
    with pytest.raises(RuntimeError, match="node-boom"):
        await compiled.invoke({})


async def test_node_error_default_handler_does_not_route_to_successor() -> None:
    g = StateGraph()

    def boom(state: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("node-boom")

    def after(state: dict[str, Any]) -> dict[str, Any]:
        return {"reached": True}

    g.add_node("boom", boom)
    g.add_node("after", after)
    g.add_edge("boom", "after")
    g.set_entry_point("boom")
    compiled = g.compile(
        retry_policy=RetryPolicy(max_attempts=1, initial_interval=0.0, jitter=False)
    )
    result = await compiled.invoke({})
    assert result["__error__"] is True
    # NOTE: the error handler swallows the failure, but successors of a failed
    # node are never scheduled, so "after" does not run.
    assert "reached" not in result


async def test_error_handler_retry_then_success() -> None:
    g = StateGraph()
    calls = {"n": 0}

    def flaky(state: dict[str, Any]) -> dict[str, Any]:
        calls["n"] += 1
        if calls["n"] < 2:
            raise ValueError("transient")
        return {"ok": True}

    g.add_node("flaky", flaky)
    g.set_entry_point("flaky")
    compiled = g.compile(
        retry_policy=RetryPolicy(max_attempts=3, initial_interval=0.0, jitter=False)
    )
    result = await compiled.invoke({})
    assert result["ok"] is True


async def test_execute_node_missing_and_terminal() -> None:
    g = StateGraph()
    g.add_node("a", lambda s: {})
    engine = PregelEngine(g)
    from app.core.engine.pregel.engine import ExecutionContext

    ctx = ExecutionContext(thread_id="t")
    with pytest.raises(ValueError, match="not found"):
        await engine._execute_node("ghost", GraphState(), {}, ctx)
    assert await engine._execute_node("__end__", GraphState(), {}, ctx) is None


async def test_debug_flag_runs() -> None:
    compiled = _linear_graph(debug=True)
    result = await compiled.invoke({})
    assert result["done"] is True


async def test_get_state_and_update_state() -> None:
    g = StateGraph()
    g.add_node("a", lambda s: {"x": 1})
    g.set_entry_point("a")
    engine = PregelEngine(g)

    empty = await engine.get_state({"thread_id": "nope"})
    assert dict(empty) == {}

    await engine.update_state({"thread_id": "t-up"}, {"x": 5})
    state = await engine.get_state({"thread_id": "t-up"})
    assert state["x"] == 5

    await engine.update_state({"thread_id": "t-up"}, {"y": 6})
    state2 = await engine.get_state({"thread_id": "t-up"})
    assert state2["x"] == 5 and state2["y"] == 6


async def test_astream_yields_states() -> None:
    compiled = _linear_graph()
    states = [s async for s in compiled.astream({"x": 0}, config={"thread_id": "t-s"})]
    assert states[-1]["done"] is True


async def test_astream_restores_checkpoint_and_resume() -> None:
    saver = InMemoryCheckpointSaver()
    g = StateGraph()

    def b(state: dict[str, Any]) -> dict[str, Any]:
        return {"done": True}

    g.add_node("b", b)
    g.add_edge("b", "__end__")
    g.set_entry_point("b")
    engine = PregelEngine(g, checkpointer=saver)
    cfg = CheckpointConfig(thread_id="t-as")
    await saver.put(cfg, Checkpoint(values={"seed": 1}, next_nodes=["b"], step=1))

    states = [s async for s in engine.astream(GraphState(), config={"thread_id": "t-as"})]
    assert states[-1]["done"] is True

    # resume value path
    states2 = [
        s
        async for s in engine.astream(
            GraphState(), config={"thread_id": "t-as2", "__resume_value__": "v"}
        )
    ]
    assert states2


async def test_astream_timeout_handler_continues() -> None:
    g = StateGraph()

    async def slow(state: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0.2)
        return {"done": True}

    g.add_node("slow", slow)
    g.set_entry_point("slow")
    engine = PregelEngine(g, timeout_policy=TimeoutPolicy(run_timeout=0.01))
    states = [s async for s in engine.astream(GraphState(), config={"thread_id": "t-at"})]
    assert states[-1].get("__error__") is True


async def test_astream_timeout_strict_reraises() -> None:
    g = StateGraph()

    async def slow(state: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0.2)
        return {"done": True}

    g.add_node("slow", slow)
    g.set_entry_point("slow")
    engine = PregelEngine(
        g,
        timeout_policy=TimeoutPolicy(run_timeout=0.01),
        error_handler=DefaultErrorHandler(continue_on_error=False),
    )
    with pytest.raises(TimeoutError):
        [s async for s in engine.astream(GraphState(), config={"thread_id": "t-at2"})]


async def test_astream_events_full_lifecycle() -> None:
    compiled = _linear_graph()
    events = [e async for e in compiled.astream_events({"x": 0}, config={"thread_id": "t-ev"})]
    types = [e.type.value for e in events]
    assert types[0] == "start"
    assert "node_start" in types
    assert "node_end" in types
    assert "checkpoint" in types
    assert types[-1] == "end"


async def test_astream_events_interrupt() -> None:
    compiled = _linear_graph(interrupt_before=["b"])
    events = [e async for e in compiled.astream_events({"x": 0}, config={"thread_id": "t-evi"})]
    assert any(e.type.value == "interrupt" for e in events)


async def test_astream_events_error_event() -> None:
    g = StateGraph()

    def boom(state: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("boom")

    g.add_node("boom", boom)
    g.set_entry_point("boom")
    engine = PregelEngine(
        g, retry_policy=RetryPolicy(max_attempts=1, initial_interval=0.0, jitter=False)
    )
    events = [e async for e in engine.astream_events(GraphState(), config={"thread_id": "t-eve"})]
    assert any(e.type.value == "error" for e in events)


async def test_astream_events_restore_and_resume_value() -> None:
    saver = InMemoryCheckpointSaver()
    g = StateGraph()

    def b(state: dict[str, Any]) -> dict[str, Any]:
        return {"done": True}

    g.add_node("b", b)
    g.add_edge("b", "__end__")
    g.set_entry_point("b")
    engine = PregelEngine(g, checkpointer=saver)
    await saver.put(
        CheckpointConfig(thread_id="t-evr"),
        Checkpoint(values={"seed": 1}, next_nodes=["b"], step=1),
    )
    events = [e async for e in engine.astream_events(GraphState(), config={"thread_id": "t-evr"})]
    assert events

    events2 = [
        e
        async for e in engine.astream_events(
            GraphState(), config={"thread_id": "t-evr2", "__resume_value__": "v"}
        )
    ]
    assert events2


async def test_astream_events_timeout_continue_and_strict() -> None:
    g = StateGraph()

    async def slow(state: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0.2)
        return {"done": True}

    g.add_node("slow", slow)
    g.set_entry_point("slow")
    engine = PregelEngine(g, timeout_policy=TimeoutPolicy(run_timeout=0.01))
    events = [e async for e in engine.astream_events(GraphState(), config={"thread_id": "t-evt"})]
    assert any(e.type.value == "error" for e in events)
    assert any(e.type.value == "end" for e in events)

    strict = PregelEngine(
        g,
        timeout_policy=TimeoutPolicy(run_timeout=0.01),
        error_handler=DefaultErrorHandler(continue_on_error=False),
    )
    with pytest.raises(TimeoutError):
        [e async for e in strict.astream_events(GraphState(), config={"thread_id": "t-evt2"})]


async def test_resume_with_public_api() -> None:
    g = StateGraph()

    def a(state: dict[str, Any]) -> dict[str, Any]:
        return {"seen": state.get("__resume_value__")}

    g.add_node("a", a)
    g.set_entry_point("a")
    engine = PregelEngine(g)
    result = await engine.resume_with({"thread_id": "t-rw"}, "answer")
    assert result["seen"] == "answer"


async def test_astream_resume_nodes_config() -> None:
    g = StateGraph()

    def a(state: dict[str, Any]) -> dict[str, Any]:
        return {"hit": "a"}

    def b(state: dict[str, Any]) -> dict[str, Any]:
        return {"hit": "b"}

    g.add_node("a", a)
    g.add_node("b", b)
    g.set_entry_point("a")
    engine = PregelEngine(g)
    states = [
        s
        async for s in engine.astream(
            GraphState(), config={"thread_id": "t-arn", "__resume_nodes__": ["b"]}
        )
    ]
    assert states[-1]["hit"] == "b"


async def test_astream_interrupt_marker_skips_entry() -> None:
    g = StateGraph()

    def a(state: dict[str, Any]) -> dict[str, Any]:
        return {"hit": "a"}

    g.add_node("a", a)
    g.set_entry_point("a")
    saver = InMemoryCheckpointSaver()
    engine = PregelEngine(g, checkpointer=saver)
    await saver.put(
        CheckpointConfig(thread_id="t-aim"),
        Checkpoint(values={"__interrupt_node__": "a"}, next_nodes=[], step=2),
    )
    states = [s async for s in engine.astream(GraphState(), config={"thread_id": "t-aim"})]
    assert len(states) == 1
    assert "hit" not in states[-1]


async def test_astream_conditional_entry_point() -> None:
    g = StateGraph()

    def a(state: dict[str, Any]) -> dict[str, Any]:
        return {"hit": "a"}

    async def router(state: dict[str, Any]) -> str:
        return "a"

    g.add_node("a", a)
    g.set_conditional_entry_point(router)
    engine = PregelEngine(g)
    states = [s async for s in engine.astream(GraphState(), config={"thread_id": "t-ace"})]
    assert states[-1]["hit"] == "a"


async def test_astream_max_steps_exhausted() -> None:
    g = StateGraph()

    def a(state: dict[str, Any]) -> dict[str, Any]:
        return {"count": state.get("count", 0) + 1}

    g.add_node("a", a)
    g.add_edge("a", "a")
    g.set_entry_point("a")
    engine = PregelEngine(g)
    states = [
        s async for s in engine.astream(GraphState(), config={"thread_id": "t-ams", "max_steps": 2})
    ]
    assert states[-1]["count"] == 2


async def test_astream_stops_on_interrupt() -> None:
    g = StateGraph()

    def a(state: dict[str, Any]) -> dict[str, Any]:
        return {"x": 1}

    def b(state: dict[str, Any]) -> dict[str, Any]:
        return {"done": True}

    g.add_node("a", a)
    g.add_node("b", b)
    g.add_edge("a", "b")
    g.set_entry_point("a")
    engine = PregelEngine(g, interrupt_before=["b"])
    states = [s async for s in engine.astream(GraphState(), config={"thread_id": "t-asi"})]
    assert states[-1]["__interrupted__"] is True
    assert "done" not in states[-1]


async def test_astream_events_resume_nodes() -> None:
    g = StateGraph()

    def a(state: dict[str, Any]) -> dict[str, Any]:
        return {"hit": "a"}

    def b(state: dict[str, Any]) -> dict[str, Any]:
        return {"hit": "b"}

    g.add_node("a", a)
    g.add_node("b", b)
    g.set_entry_point("a")
    engine = PregelEngine(g)
    events = [
        e
        async for e in engine.astream_events(
            GraphState(), config={"thread_id": "t-aern", "__resume_nodes__": ["b"]}
        )
    ]
    assert events


async def test_astream_events_interrupt_marker_skips_entry() -> None:
    g = StateGraph()

    def a(state: dict[str, Any]) -> dict[str, Any]:
        return {"hit": "a"}

    g.add_node("a", a)
    g.set_entry_point("a")
    saver = InMemoryCheckpointSaver()
    engine = PregelEngine(g, checkpointer=saver)
    await saver.put(
        CheckpointConfig(thread_id="t-aeim"),
        Checkpoint(values={"__interrupt_node__": "a"}, next_nodes=[], step=2),
    )
    events = [e async for e in engine.astream_events(GraphState(), config={"thread_id": "t-aeim"})]
    assert events[-1].type.value == "end"


async def test_astream_events_conditional_entry_point() -> None:
    g = StateGraph()

    def a(state: dict[str, Any]) -> dict[str, Any]:
        return {"hit": "a"}

    async def router(state: dict[str, Any]) -> str:
        return "a"

    g.add_node("a", a)
    g.set_conditional_entry_point(router)
    engine = PregelEngine(g)
    events = [e async for e in engine.astream_events(GraphState(), config={"thread_id": "t-aece"})]
    assert any(e.type.value == "node_end" for e in events)


async def test_astream_events_max_steps_exhausted() -> None:
    g = StateGraph()

    def a(state: dict[str, Any]) -> dict[str, Any]:
        return {"count": state.get("count", 0) + 1}

    g.add_node("a", a)
    g.add_edge("a", "a")
    g.set_entry_point("a")
    engine = PregelEngine(g)
    events = [
        e
        async for e in engine.astream_events(
            GraphState(), config={"thread_id": "t-aems", "max_steps": 2}
        )
    ]
    # loop exhausts max_steps without an explicit END event from the empty check
    assert any(e.type.value == "node_end" for e in events)


async def test_astream_events_without_checkpoint_id(monkeypatch) -> None:
    from app.core.engine.pregel.engine import SuperStepResult

    g = StateGraph()
    g.add_node("a", lambda s: {"x": 1})
    g.set_entry_point("a")
    engine = PregelEngine(g)

    async def fake_super_step(state, config, context):
        return SuperStepResult(
            step=1,
            node_results={"a": {"x": 1}},
            active_nodes=["a"],
            next_active=[],
            checkpoint_id=None,
        )

    monkeypatch.setattr(engine, "_execute_super_step", fake_super_step)
    events = [e async for e in engine.astream_events(GraphState(), config={"thread_id": "t-aenc"})]
    assert not any(e.type.value == "checkpoint" for e in events)


async def test_interrupt_after_command_marks_metadata() -> None:
    g = StateGraph()

    def a(state: dict[str, Any]) -> Command:
        return Command(update={"x": 1})

    g.add_node("a", a)
    g.set_entry_point("a")
    engine = PregelEngine(g, interrupt_after=["a"])
    result = await engine.run(GraphState(), config={"thread_id": "t-iac"})
    assert result["__interrupted__"] is True


async def test_entry_resolution_without_entry_or_branch() -> None:
    # Bypass compile() validation: a raw graph with no entry point and no
    # __start__ conditional edge leaves entry as None.
    g = StateGraph()
    g.add_node("a", lambda s: {"x": 1})
    engine = PregelEngine(g)

    states = [s async for s in engine.astream(GraphState(), config={"thread_id": "t-none"})]
    assert len(states) == 1

    events = [e async for e in engine.astream_events(GraphState(), config={"thread_id": "t-none2"})]
    assert events[0].type.value == "start"
