"""Coverage tests for app.core.engine.pregel.state."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from app.core.engine.pregel.state import (
    GraphState,
    StateReducer,
    add_reducer,
    merge_dicts_reducer,
    merge_states,
    overwrite_reducer,
)


class _StateSchema(TypedDict):
    items: Annotated[list[int], add_reducer]
    other: int


class _MixedSchema(TypedDict):
    nums: list[int]
    weird: Annotated[list[int], "notcallable"]


def test_state_reducer_skips_non_reducer_hints() -> None:
    reducer = StateReducer(_MixedSchema)
    assert reducer.get_reducer("nums") is overwrite_reducer
    assert reducer.get_reducer("weird") is overwrite_reducer


def test_add_reducer_variants() -> None:
    assert add_reducer(None, None) == []
    assert add_reducer(None, [1, 2]) == [1, 2]
    assert add_reducer([1], [2, 3]) == [1, 2, 3]
    assert add_reducer([1], 2) == [1, 2]


def test_overwrite_reducer() -> None:
    assert overwrite_reducer("old", "new") == "new"


def test_merge_dicts_reducer_variants() -> None:
    assert merge_dicts_reducer(None, None) == {}
    assert merge_dicts_reducer(None, {"a": 1}) == {"a": 1}
    assert merge_dicts_reducer({"a": 1}, None) == {"a": 1}
    assert merge_dicts_reducer({"a": {"x": 1}}, {"a": {"y": 2}}) == {"a": {"x": 1, "y": 2}}
    assert merge_dicts_reducer({"a": 1}, {"a": 2}) == {"a": 2}


def test_state_reducer_parses_schema_and_registers() -> None:
    reducer = StateReducer(_StateSchema)
    assert reducer.get_reducer("items") is add_reducer
    # unmapped field falls back to overwrite
    assert reducer.get_reducer("other") is overwrite_reducer

    custom = StateReducer()
    custom.register("k", operator.add)
    assert custom.get_reducer("k") is operator.add
    # schema without callable reducer second arg is ignored
    assert StateReducer(int).get_reducer("nope") is overwrite_reducer


def test_graph_state_merge_update_and_metadata() -> None:
    state = GraphState({"items": [1]}, schema=_StateSchema)
    state.merge_update({"items": [2], "other": 5, "__skip__": 9})
    assert state["items"] == [1, 2]
    assert state["other"] == 5
    assert "__skip__" not in state


def test_graph_state_properties_and_clone() -> None:
    state = GraphState({"a": [1]}, schema=_StateSchema)
    state.step = 7
    state.current_node = "node-1"
    state.metadata["k"] = "v"
    assert state.step == 7
    assert state.current_node == "node-1"
    assert state.metadata == {"k": "v"}

    clone = state.clone()
    clone["a"].append(2)
    clone.metadata["k"] = "changed"
    # deep copy of values, shallow copy of metadata container
    assert state["a"] == [1]
    assert clone["a"] == [1, 2]
    assert clone.step == 7
    assert clone.current_node == "node-1"
    assert clone._reducer is state._reducer


def test_merge_states_with_and_without_reducers() -> None:
    base = {"items": [1], "keep": "x"}
    assert merge_states(base, {"items": [2]}, {"items": add_reducer}) == {
        "items": [1, 2],
        "keep": "x",
    }
    assert merge_states(base, {"new": 3}) == {"items": [1], "keep": "x", "new": 3}
    # base is not mutated
    assert base == {"items": [1], "keep": "x"}
