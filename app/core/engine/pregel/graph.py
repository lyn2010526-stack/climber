"""StateGraph definition and compilation.

StateGraph is the builder API for defining graph topology:
- Nodes: async callables that transform state
- Edges: routing between nodes
- Conditional edges: dynamic routing based on state
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

import structlog

from app.core.engine.pregel.checkpoint import Checkpoint
from app.core.engine.pregel.command import Command
from app.core.engine.pregel.state import GraphState, StateReducer

logger = structlog.get_logger(__name__)

NodeFunc = Callable[[GraphState], Awaitable[dict | Command | str] | dict | Command | str]
RouterFunc = Callable[[GraphState], str | Awaitable[str]]


@runtime_checkable
class CompiledGraph(Protocol):
    """Protocol for a compiled, executable graph."""

    async def invoke(self, input: dict, config: dict | None = None) -> dict: ...
    async def astream(self, input: dict, config: dict | None = None) -> Any: ...
    async def astream_events(self, input: dict, config: dict | None = None) -> Any: ...
    async def get_state(self, config: dict) -> GraphState: ...
    async def get_state_history(self, config: dict, *, limit: int = 10, before: str | None = None) -> list[Checkpoint]: ...
    async def update_state(self, config: dict, values: dict) -> dict: ...
    async def fork(self, config: dict, *, new_thread_id: str, values: dict | None = None) -> dict: ...


class Branch:
    """A conditional branch from a node."""

    def __init__(self, router: RouterFunc, path_map: dict[str, str] | None = None) -> None:
        self.router = router
        self.path_map = path_map or {}


class StateGraph:
    """Builder for defining a state graph.

    Example:
        graph = StateGraph(MyState)
        graph.add_node("chat", chat_node)
        graph.add_node("tools", tools_node)
        graph.add_edge("chat", "tools")
        graph.add_conditional_edges("tools", should_retry, {"yes": "chat", "no": "__end__"})
        graph.set_entry_point("chat")
        app = graph.compile()
    """

    def __init__(self, state_schema: type | None = None) -> None:
        self._schema = state_schema
        self._reducer = StateReducer(state_schema)
        self._nodes: dict[str, NodeFunc] = {}
        self._edges: list[tuple[str, str]] = []
        self._conditional_edges: dict[str, Branch] = {}
        self._entry_point: str | None = None
        self._branches: dict[str, dict[str, Branch]] = defaultdict(dict)

    @property
    def schema(self) -> type | None:
        return self._schema

    def add_node(self, name: str, func: NodeFunc) -> StateGraph:
        """Register a node function.

        Args:
            name: Unique node identifier.
            func: Callable that receives state and returns updates.

        Returns:
            Self for chaining.
        """
        if name in self._nodes:
            logger.warning("node_overwrite", node=name)
        self._nodes[name] = func
        return self

    def add_edge(self, src: str, dst: str) -> StateGraph:
        """Add a directed edge from src to dst.

        Args:
            src: Source node name.
            dst: Target node name.

        Returns:
            Self for chaining.
        """
        self._edges.append((src, dst))
        logger.debug("edge_added", src=src, dst=dst)
        return self

    def add_conditional_edges(
        self,
        src: str,
        router: RouterFunc,
        path_map: dict[str, str] | None = None,
    ) -> StateGraph:
        """Add conditional routing from a source node.

        Args:
            src: Source node name.
            router: Callable that returns the next node name.
            path_map: Optional mapping of router output -> node name.

        Returns:
            Self for chaining.
        """
        self._conditional_edges[src] = Branch(router, path_map)
        logger.debug("conditional_edge_added", src=src)
        return self

    def add_sequence(self, *nodes: str) -> StateGraph:
        """Add a linear sequence of edges between nodes.

        Args:
            nodes: Ordered list of node names.

        Returns:
            Self for chaining.
        """
        for i in range(len(nodes) - 1):
            self.add_edge(nodes[i], nodes[i + 1])
        return self

    def set_entry_point(self, node: str) -> StateGraph:
        """Set the starting node for execution.

        Args:
            node: Name of the entry node.

        Returns:
            Self for chaining.
        """
        self._entry_point = node
        return self

    def set_conditional_entry_point(
        self,
        router: RouterFunc,
        path_map: dict[str, str] | None = None,
    ) -> StateGraph:
        """Set a conditional entry point.

        Args:
            router: Callable that returns the starting node name.
            path_map: Optional mapping of router output -> node name.

        Returns:
            Self for chaining.
        """
        self._conditional_edges["__start__"] = Branch(router, path_map)
        return self

    def compile(
        self,
        *,
        checkpointer: Any = None,
        interrupt_before: list[str] | None = None,
        interrupt_after: list[str] | None = None,
        debug: bool = False,
    ) -> CompiledGraph:
        """Compile the graph into an executable form.

        Args:
            checkpointer: Optional checkpoint saver for persistence.
            interrupt_before: Nodes to interrupt before execution.
            interrupt_after: Nodes to interrupt after execution.
            debug: Enable verbose debug logging.

        Returns:
            A CompiledGraph instance ready for execution.
        """
        self._validate()

        from app.core.engine.pregel.engine import PregelEngine

        return CompiledGraphImpl(
            graph=self,
            engine=PregelEngine(
                graph=self,
                checkpointer=checkpointer,
                interrupt_before=interrupt_before or [],
                interrupt_after=interrupt_after or [],
                debug=debug,
            ),
        )

    def _validate(self) -> None:
        """Validate graph configuration before compilation."""
        if not self._nodes:
            raise ValueError("Graph has no nodes")
        if not self._entry_point and "__start__" not in self._conditional_edges:
            raise ValueError("No entry point set. Call set_entry_point() or set_conditional_entry_point()")
        if self._entry_point and self._entry_point not in self._nodes:
            raise ValueError(f"Entry point '{self._entry_point}' is not a registered node")
        for src, dst in self._edges:
            if src not in self._nodes:
                raise ValueError(f"Edge source '{src}' is not a registered node")
            if dst not in self._nodes and dst != "__end__":
                raise ValueError(f"Edge target '{dst}' is not a registered node")

    def get_node(self, name: str) -> NodeFunc | None:
        """Get a registered node function."""
        return self._nodes.get(name)

    def get_outgoing_edges(self, node: str) -> list[str]:
        """Get all direct successors of a node."""
        return [dst for src, dst in self._edges if src == node]

    def get_conditional_edges(self, node: str) -> Branch | None:
        """Get the conditional branch for a node."""
        return self._conditional_edges.get(node)

    @property
    def nodes(self) -> set[str]:
        return set(self._nodes.keys())

    @property
    def edges(self) -> list[tuple[str, str]]:
        return list(self._edges)


class CompiledGraphImpl:
    """Compiled graph that can be invoked."""

    def __init__(self, graph: StateGraph, engine: Any) -> None:
        self._graph = graph
        self._engine = engine

    @property
    def graph(self) -> StateGraph:
        return self._graph

    async def invoke(self, input: dict, config: dict | None = None) -> dict:
        """Execute the graph synchronously and return final state.

        Args:
            input: Initial state values.
            config: Execution config (thread_id, checkpoint_id, etc.).

        Returns:
            Final state dict after graph completes.
        """
        config = config or {}
        state = GraphState(input, schema=self._graph.schema)
        result = await self._engine.run(state, config=config)
        return dict(result)

    async def astream(self, input: dict, config: dict | None = None):
        """Stream state updates after each super-step.

        Args:
            input: Initial state values.
            config: Execution config.

        Yields:
            State dict after each super-step.
        """
        config = config or {}
        state = GraphState(input, schema=self._graph.schema)
        async for step_state in self._engine.astream(state, config=config):
            yield dict(step_state)

    async def astream_events(self, input: dict, config: dict | None = None):
        """Stream detailed execution events.

        Args:
            input: Initial state values.
            config: Execution config.

        Yields:
            StreamEvent objects with node-level detail.
        """
        config = config or {}
        state = GraphState(input, schema=self._graph.schema)
        async for event in self._engine.astream_events(state, config=config):
            yield event

    async def get_state(self, config: dict) -> GraphState:
        """Get the current state for a thread."""
        return await self._engine.get_state(config)

    async def get_state_history(
        self,
        config: dict,
        *,
        limit: int = 10,
        before: str | None = None,
    ) -> list[Checkpoint]:
        """Get checkpoint history for a thread, newest first."""
        return await self._engine.get_state_history(config, limit=limit, before=before)

    async def update_state(self, config: dict, values: dict) -> dict:
        """Update the state for a thread."""
        return await self._engine.update_state(config, values)

    async def resume_with(self, config: dict, value: Any) -> dict:
        """Resume from an interrupt with a value."""
        return await self._engine.resume_with(config, value)

    async def fork(
        self,
        config: dict,
        *,
        new_thread_id: str,
        values: dict | None = None,
    ) -> dict:
        """Fork a checkpoint into a new thread and continue execution."""
        return await self._engine.fork(
            config,
            new_thread_id=new_thread_id,
            values=values,
        )
