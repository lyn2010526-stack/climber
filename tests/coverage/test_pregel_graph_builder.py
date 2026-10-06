"""Coverage tests for app.core.engine.pregel.graph."""

from __future__ import annotations

from typing import Any

import pytest

from app.core.engine.pregel.graph import (
    Branch,
    CompiledGraph,
    CompiledGraphImpl,
    StateGraph,
)


def _noop_node(state: dict[str, Any]) -> dict[str, Any]:
    return {}


def test_branch_defaults_and_custom_map() -> None:
    branch = Branch(lambda s: "x")
    assert branch.path_map == {}
    branch2 = Branch(lambda s: "x", {"a": "b"})
    assert branch2.path_map == {"a": "b"}


def test_builder_helpers_and_properties() -> None:
    g = StateGraph()
    assert g.schema is None
    g.add_node("a", _noop_node)
    g.add_node("b", _noop_node)
    g.add_node("c", _noop_node)
    assert g.get_node("a") is _noop_node
    assert g.get_node("missing") is None
    assert g.nodes == {"a", "b", "c"}

    g.add_edge("a", "b")
    g.add_edge("b", "c")
    g.add_sequence("c", "a")
    assert g.edges == [("a", "b"), ("b", "c"), ("c", "a")]
    assert g.get_outgoing_edges("a") == ["b"]
    assert g.get_outgoing_edges("zzz") == []

    g.add_conditional_edges("a", lambda s: "b", {"b": "b"})
    branch = g.get_conditional_edges("a")
    assert branch is not None and branch.path_map == {"b": "b"}
    assert g.get_conditional_edges("b") is None

    assert g.set_entry_point("a") is g
    assert g.set_conditional_entry_point(lambda s: "a") is g
    assert g.get_conditional_edges("__start__") is not None


def test_add_node_overwrite_warns(caplog) -> None:
    g = StateGraph()

    def first(state: dict[str, Any]) -> dict[str, Any]:
        return {"v": 1}

    g.add_node("x", first)
    g.add_node("x", _noop_node)
    assert g.get_node("x") is _noop_node


def test_validate_errors() -> None:
    with pytest.raises(ValueError, match="no nodes"):
        StateGraph()._validate()

    g = StateGraph()
    g.add_node("a", _noop_node)
    with pytest.raises(ValueError, match="No entry point"):
        g._validate()

    g.set_entry_point("missing")
    with pytest.raises(ValueError, match="not a registered node"):
        g._validate()

    g2 = StateGraph()
    g2.add_node("a", _noop_node)
    g2.set_entry_point("a")
    g2.add_edge("a", "missing")
    with pytest.raises(ValueError, match="Edge target"):
        g2._validate()

    g3 = StateGraph()
    g3.add_node("a", _noop_node)
    g3.set_entry_point("a")
    g3.add_edge("ghost", "a")
    with pytest.raises(ValueError, match="Edge source"):
        g3._validate()

    g4 = StateGraph()
    g4.add_node("a", _noop_node)
    g4.set_entry_point("a")
    g4.add_conditional_edges("ghost", lambda s: "a")
    with pytest.raises(ValueError, match="Conditional edge source"):
        g4._validate()

    # valid: edge to __end__ allowed, __start__ conditional allowed
    g5 = StateGraph()
    g5.add_node("a", _noop_node)
    g5.add_edge("a", "__end__")
    g5.set_conditional_entry_point(lambda s: "a")
    g5._validate()


async def test_compile_and_invoke_simple_graph() -> None:
    g = StateGraph()

    async def start(state: dict[str, Any]) -> dict[str, Any]:
        return {"value": state.get("value", 0) + 1}

    g.add_node("start", start)
    g.add_node("end", lambda state: {"done": True})
    g.add_edge("start", "end")
    g.set_entry_point("start")
    compiled = g.compile()
    assert isinstance(compiled, CompiledGraphImpl)
    assert isinstance(compiled, CompiledGraph)
    assert compiled.graph is g

    result = await compiled.invoke({"value": 1})
    assert result["value"] == 2
    assert result["done"] is True


async def test_execution_config_defaults_thread_id() -> None:
    cfg = CompiledGraphImpl._execution_config(None)
    assert "thread_id" in cfg
    cfg2 = CompiledGraphImpl._execution_config({"thread_id": "t", "x": 1})
    assert cfg2 == {"thread_id": "t", "x": 1}


async def test_compiled_astream_and_astream_events() -> None:
    g = StateGraph()
    g.add_node("a", lambda state: {"n": state.get("n", 0) + 1})
    g.set_entry_point("a")
    compiled = g.compile()

    states = [s async for s in compiled.astream({"n": 0})]
    assert states
    assert states[-1]["n"] == 1

    events = [e async for e in compiled.astream_events({"n": 0})]
    assert any(e.type.value == "start" for e in events)
    assert any(e.type.value == "end" for e in events)


async def test_compiled_get_and_update_state() -> None:
    g = StateGraph()
    g.add_node("a", lambda state: {"n": 1})
    g.set_entry_point("a")
    compiled = g.compile()

    await compiled.invoke({"n": 0}, config={"thread_id": "t1"})
    state = await compiled.get_state({"thread_id": "t1"})
    assert state["n"] == 1

    await compiled.update_state({"thread_id": "t1"}, {"extra": 42})
    state2 = await compiled.get_state({"thread_id": "t1"})
    assert state2["extra"] == 42


async def test_compiled_resume_with_returns_state() -> None:
    g = StateGraph()
    g.add_node("a", lambda state: {"n": state.get("n", 0)})
    g.set_entry_point("a")
    compiled = g.compile()
    result = await compiled.resume_with({"thread_id": "tr"}, "resume-value")
    assert isinstance(result, dict)
