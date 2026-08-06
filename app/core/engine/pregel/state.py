"""State management with reducer-based merging.

Reducers control how state values are updated when a node returns a partial
state dict. Without a reducer, the default behavior is last-write-wins.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any, TypeVar, get_args, get_origin, get_type_hints

import structlog

logger = structlog.get_logger(__name__)

StateT = TypeVar("StateT", bound=dict)

ReducerFn = Callable[[Any, Any], Any]


def add_reducer(existing: list, new: list) -> list:
    """Append new values to existing list."""
    if existing is None:
        return list(new) if new else []
    result = list(existing)
    if isinstance(new, list):
        result.extend(new)
    else:
        result.append(new)
    return result


def overwrite_reducer(existing: Any, new: Any) -> Any:
    """Replace existing value entirely."""
    return new


def merge_dicts_reducer(existing: dict | None, new: dict | None) -> dict:
    """Deep merge two dictionaries."""
    if existing is None:
        return dict(new) if new else {}
    if new is None:
        return dict(existing)
    result = dict(existing)
    for key, value in new.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts_reducer(result[key], value)
        else:
            result[key] = value
    return result


class StateReducer:
    """Registry of reducers for state fields."""

    def __init__(self, schema: type | None = None) -> None:
        self._reducers: dict[str, ReducerFn] = {}
        self._schema = schema
        if schema:
            self._parse_schema(schema)

    def _parse_schema(self, schema: type) -> None:
        """Extract reducers from Annotated type hints."""
        hints = get_type_hints(schema, include_extras=True)
        for field_name, hint in hints.items():
            origin = get_origin(hint)
            if origin is not None:
                args = get_args(hint)
                if len(args) >= 2:
                    reducer = args[1]
                    if callable(reducer):
                        self._reducers[field_name] = reducer
                        logger.debug("reducer_registered", field=field_name)

    def get_reducer(self, key: str) -> ReducerFn:
        """Get the reducer for a state key."""
        return self._reducers.get(key, overwrite_reducer)

    def register(self, key: str, reducer: ReducerFn) -> None:
        """Register a reducer for a specific key."""
        self._reducers[key] = reducer


class GraphState(dict):
    """Typed state container for graph execution.

    Extends dict with reducer-aware merge semantics.
    """

    def __init__(self, *args, schema: type | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._reducer = StateReducer(schema)
        self._step: int = 0
        self._node: str | None = None
        self._metadata: dict[str, Any] = {}

    @property
    def step(self) -> int:
        return self._step

    @step.setter
    def step(self, value: int) -> None:
        self._step = value

    @property
    def current_node(self) -> str | None:
        return self._node

    @current_node.setter
    def current_node(self, value: str | None) -> None:
        self._node = value

    @property
    def metadata(self) -> dict[str, Any]:
        return self._metadata

    def merge_update(self, update: dict[str, Any]) -> GraphState:
        """Merge an update dict using registered reducers."""
        for key, value in update.items():
            if key.startswith("__"):
                continue
            reducer = self._reducer.get_reducer(key)
            existing = self.get(key)
            self[key] = reducer(existing, value)
        return self

    def clone(self) -> GraphState:
        """Create a deep copy of this state."""
        new_state = GraphState(copy.deepcopy(dict(self)))
        new_state._reducer = self._reducer
        new_state._step = self._step
        new_state._node = self._node
        new_state._metadata = dict(self._metadata)
        return new_state


def merge_states(base: dict, update: dict, reducers: dict[str, ReducerFn] | None = None) -> dict:
    """Merge update into base using optional reducers for each key.

    Args:
        base: The existing state dict.
        update: New values to merge in.
        reducers: Optional mapping of key -> reducer function.

    Returns:
        A new dict with merged values.
    """
    result = dict(base)
    reducers = reducers or {}
    for key, value in update.items():
        if key in reducers:
            result[key] = reducers[key].__call__(result.get(key), value)
        else:
            result[key] = value
    return result
