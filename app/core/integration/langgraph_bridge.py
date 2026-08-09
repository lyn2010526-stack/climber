"""LangGraph integration bridge.

Bridges the existing Pregel engine with LangGraph's production-grade runtime,
enabling access to LangGraph's checkpointing, streaming, and tool calling.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.core.engine.pregel import (
    GraphState,
)

logger = logging.getLogger(__name__)


class LangGraphBridge:
    """Bridge that wraps a LangGraph StateGraph with the existing engine interface."""

    def __init__(self, checkpointer: bool = True):
        self._graphs: dict[str, StateGraph] = {}
        self._compiled: dict[str, Any] = {}
        self._checkpointer = MemorySaver() if checkpointer else None

    def register_graph(self, name: str, graph: StateGraph) -> None:
        """Register a LangGraph StateGraph."""
        self._graphs[name] = graph
        self._compiled[name] = graph.compile(checkpointer=self._checkpointer)
        logger.info("langgraph_registered", name=name)

    def create_simple_graph(
        self,
        name: str,
        nodes: dict[str, Callable],
        edges: list[tuple[str, str | Callable]],
        entry_point: str | None = None,
    ) -> StateGraph:
        """Create and register a simple StateGraph from node functions and edges."""
        graph = StateGraph(GraphState)

        for node_name, node_func in nodes.items():
            graph.add_node(node_name, node_func)

        for source, target in edges:
            if callable(target):
                graph.add_conditional_edges(source, target)
            elif target == END:
                graph.add_edge(source, END)
            else:
                graph.add_edge(source, target)

        if entry_point:
            graph.set_entry_point(entry_point)

        self.register_graph(name, graph)
        return graph

    async def invoke(
        self,
        name: str,
        inputs: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Invoke a registered graph."""
        if name not in self._compiled:
            raise ValueError(f"Graph '{name}' not registered")

        cfg = {"configurable": config or {}}
        result = await self._compiled[name].ainvoke(inputs, cfg)
        return result

    async def astream(
        self,
        name: str,
        inputs: dict[str, Any],
        config: dict[str, Any] | None = None,
    ):
        """Stream graph execution events."""
        if name not in self._compiled:
            raise ValueError(f"Graph '{name}' not registered")

        cfg = {"configurable": config or {}}
        async for event in self._compiled[name].astream(inputs, cfg):
            yield event

    def get_graph(self, name: str) -> StateGraph | None:
        return self._graphs.get(name)

    def list_graphs(self) -> list[str]:
        return list(self._graphs.keys())

    def get_state(self, name: str, config: dict[str, Any]) -> dict[str, Any] | None:
        """Get current state for a thread."""
        if name not in self._compiled:
            return None
        try:
            snapshot = self._compiled[name].get_state(config)
            return snapshot.values if snapshot else None
        except Exception:
            return None

    def update_state(
        self,
        name: str,
        config: dict[str, Any],
        values: dict[str, Any],
    ) -> None:
        """Update state for a thread."""
        if name not in self._compiled:
            raise ValueError(f"Graph '{name}' not registered")
        self._compiled[name].update_state(config, values)


# Global bridge instance
_bridge: LangGraphBridge | None = None


def get_bridge(checkpointer: bool = True) -> LangGraphBridge:
    """Get or create the global LangGraph bridge."""
    global _bridge
    if _bridge is None:
        _bridge = LangGraphBridge(checkpointer=checkpointer)
    return _bridge
