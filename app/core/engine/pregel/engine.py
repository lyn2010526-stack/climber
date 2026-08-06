"""Pregel execution engine with super-step semantics.

Executes the compiled graph using the Pregel model:
1. Each super-step identifies active nodes (those with pending work)
2. Active nodes execute in parallel
3. Outputs are routed to next nodes via edges or commands
4. State is merged using reducers
5. Repeat until no nodes are active or max_steps reached
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.core.engine.pregel.checkpoint import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointConfig,
    InMemoryCheckpointSaver,
)
from app.core.engine.pregel.command import Command, is_command, parse_node_output
from app.core.engine.pregel.graph import StateGraph
from app.core.engine.pregel.hitl import HITLManager
from app.core.engine.pregel.policies import (
    DefaultErrorHandler,
    ErrorHandler,
    RetryPolicy,
    TimeoutPolicy,
    execute_with_retry,
)
from app.core.engine.pregel.state import GraphState
from app.core.engine.pregel.streaming import StreamEvent, StreamEventType

logger = structlog.get_logger(__name__)


@dataclass
class SuperStepResult:
    """Result of a single super-step execution."""

    step: int
    node_results: dict[str, Any] = field(default_factory=dict)
    active_nodes: list[str] = field(default_factory=list)
    next_active: list[str] = field(default_factory=list)
    interrupted: bool = False
    checkpoint_id: str | None = None
    errors: dict[str, Exception] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Final result of graph execution."""

    final_state: dict[str, Any]
    total_steps: int
    checkpoint_ids: list[str] = field(default_factory=list)
    interrupted: bool = False
    interrupt_node: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionContext:
    """Mutable execution data isolated to one graph invocation."""

    thread_id: str
    active_nodes: list[str] = field(default_factory=list)
    step: int = 0
    checkpoint_ids: list[str] = field(default_factory=list)
    skip_interrupt_before: set[str] = field(default_factory=set)


class PregelEngine:
    """Super-step based execution engine for StateGraph."""

    def __init__(
        self,
        graph: StateGraph,
        checkpointer: BaseCheckpointSaver | None = None,
        interrupt_before: list[str] | None = None,
        interrupt_after: list[str] | None = None,
        retry_policy: RetryPolicy | None = None,
        timeout_policy: TimeoutPolicy | None = None,
        error_handler: ErrorHandler | None = None,
        hitl_manager: HITLManager | None = None,
        debug: bool = False,
    ) -> None:
        self._graph = graph
        self._checkpointer = checkpointer or InMemoryCheckpointSaver()
        self._interrupt_before = set(interrupt_before or [])
        self._interrupt_after = set(interrupt_after or [])
        self._retry_policy = retry_policy or RetryPolicy()
        self._timeout_policy = timeout_policy or TimeoutPolicy()
        self._error_handler = error_handler or DefaultErrorHandler()
        self._hitl = hitl_manager or HITLManager()
        self._debug = debug

    async def run(self, state: GraphState, config: dict | None = None) -> GraphState:
        """Run the graph until completion.

        Args:
            state: Initial graph state.
            config: Execution configuration.

        Returns:
            Final state after graph completes.
        """
        config = dict(config or {})
        thread_id = config.setdefault("thread_id", str(uuid.uuid4()))
        max_steps = config.get("max_steps", 100)
        context = ExecutionContext(thread_id=thread_id)

        # Check for resume config
        resume_value = config.get("__resume_value__")
        resume_nodes = config.get("__resume_nodes__")

        # Restore from checkpoint if available
        checkpoint_config = CheckpointConfig(thread_id=thread_id)
        existing = await self._checkpointer.get(checkpoint_config)
        if existing:
            logger.info("restoring_from_checkpoint", thread_id=thread_id, step=existing.step)
            state = GraphState(existing.values, schema=self._graph.schema)
            state.step = existing.step
            context.step = existing.step
            context.active_nodes = list(existing.next_nodes)
            if resume_value is not None and existing.metadata.get("interrupt_type") == "before":
                context.skip_interrupt_before.update(existing.next_nodes)

        # Apply resume value if present
        if resume_value is not None:
            state["__resume_value__"] = resume_value
            state["__interrupted__"] = False

        if resume_nodes:
            context.active_nodes = resume_nodes
        elif not context.active_nodes:
            # Check if we're resuming from an interrupt
            interrupt_node = state.get("__interrupt_node__")
            if interrupt_node and state.get("__interrupted__"):
                context.active_nodes = list(existing.next_nodes) if existing else []
            else:
                entry = self._graph._entry_point
                if entry is None:
                    entry = "__start__"
                branch = self._graph.get_conditional_edges("__start__")
                if branch:
                    next_node = await self._resolve_router(branch.router, state)
                    entry = next_node
                context.active_nodes = [entry] if entry else []

        async def execute() -> None:
            for _ in range(max_steps):
                if not context.active_nodes:
                    logger.info("execution_complete", steps=context.step)
                    break
                step_result = await self._execute_super_step(state, config, context)
                state.step = context.step
                context.active_nodes = step_result.next_active
                if step_result.interrupted:
                    logger.info("execution_interrupted", node=step_result.active_nodes, step=context.step)
                    break

        try:
            if self._timeout_policy.run_timeout is None:
                await execute()
            else:
                await asyncio.wait_for(execute(), timeout=self._timeout_policy.run_timeout)
        except TimeoutError as error:
            handler_result = await self._error_handler.handle(error, dict(state), "__run__")
            if handler_result is None:
                raise
            self._merge_error_update(state, handler_result)

        return state

    async def astream(self, state: GraphState, config: dict | None = None) -> AsyncIterator[GraphState]:
        """Stream state after each super-step.

        Args:
            state: Initial graph state.
            config: Execution configuration.

        Yields:
            State dict after each super-step.
        """
        config = dict(config or {})
        thread_id = config.setdefault("thread_id", str(uuid.uuid4()))
        max_steps = config.get("max_steps", 100)
        context = ExecutionContext(thread_id=thread_id)

        checkpoint_config = CheckpointConfig(thread_id=thread_id)
        existing = await self._checkpointer.get(checkpoint_config)
        if existing:
            state = GraphState(existing.values, schema=self._graph.schema)
            state.step = existing.step
            context.step = existing.step
            context.active_nodes = list(existing.next_nodes)

        if not context.active_nodes:
            entry = self._graph._entry_point
            if entry is None:
                branch = self._graph.get_conditional_edges("__start__")
                if branch:
                    entry = await self._resolve_router(branch.router, state)
            context.active_nodes = [entry] if entry else []

        yield state.clone()

        try:
            async with asyncio.timeout(self._timeout_policy.run_timeout):
                for _ in range(max_steps):
                    if not context.active_nodes:
                        break
                    step_result = await self._execute_super_step(state, config, context)
                    state.step = context.step
                    yield state.clone()
                    context.active_nodes = step_result.next_active
                    if step_result.interrupted:
                        break
        except TimeoutError as error:
            handler_result = await self._error_handler.handle(error, dict(state), "__run__")
            if handler_result is None:
                raise
            self._merge_error_update(state, handler_result)
            yield state.clone()

    async def astream_events(self, state: GraphState, config: dict | None = None) -> AsyncIterator[StreamEvent]:
        """Stream detailed execution events.

        Args:
            state: Initial graph state.
            config: Execution configuration.

        Yields:
            StreamEvent objects.
        """
        config = dict(config or {})
        thread_id = config.setdefault("thread_id", str(uuid.uuid4()))
        max_steps = config.get("max_steps", 100)
        context = ExecutionContext(thread_id=thread_id)

        checkpoint_config = CheckpointConfig(thread_id=thread_id)
        existing = await self._checkpointer.get(checkpoint_config)
        if existing:
            state = GraphState(existing.values, schema=self._graph.schema)
            state.step = existing.step
            context.step = existing.step
            context.active_nodes = list(existing.next_nodes)

        if not context.active_nodes:
            entry = self._graph._entry_point
            if entry is None:
                branch = self._graph.get_conditional_edges("__start__")
                if branch:
                    entry = await self._resolve_router(branch.router, state)
            context.active_nodes = [entry] if entry else []

        yield StreamEvent(type=StreamEventType.START, data={"input": dict(state)})

        try:
            async with asyncio.timeout(self._timeout_policy.run_timeout):
                for _ in range(max_steps):
                    if not context.active_nodes:
                        yield StreamEvent(type=StreamEventType.END, data={"total_steps": context.step})
                        break

                    for node in context.active_nodes:
                        yield StreamEvent(
                            type=StreamEventType.NODE_START,
                            data={"node": node},
                            node=node,
                            step=context.step,
                        )

                    step_result = await self._execute_super_step(state, config, context)
                    state.step = context.step

                    for node, result in step_result.node_results.items():
                        yield StreamEvent(
                            type=StreamEventType.NODE_END,
                            data={"node": node, "result": result},
                            node=node,
                            step=context.step,
                        )
                    for node, error in step_result.errors.items():
                        yield StreamEvent(
                            type=StreamEventType.ERROR,
                            data={"error": str(error), "error_type": type(error).__name__},
                            node=node,
                            step=context.step,
                        )
                    if step_result.checkpoint_id:
                        yield StreamEvent(
                            type=StreamEventType.CHECKPOINT,
                            data={"checkpoint_id": step_result.checkpoint_id},
                            step=context.step,
                        )

                    context.active_nodes = step_result.next_active
                    if step_result.interrupted:
                        yield StreamEvent(
                            type=StreamEventType.INTERRUPT,
                            data={"node": step_result.active_nodes},
                            step=context.step,
                        )
                        break
        except TimeoutError as error:
            handler_result = await self._error_handler.handle(error, dict(state), "__run__")
            if handler_result is None:
                yield StreamEvent(type=StreamEventType.ERROR, data={"error": str(error)})
                raise
            self._merge_error_update(state, handler_result)
            yield StreamEvent(
                type=StreamEventType.ERROR,
                data={"error": str(error), "error_type": type(error).__name__},
                node="__run__",
                step=context.step,
            )
            yield StreamEvent(type=StreamEventType.END, data={"total_steps": context.step})

    async def get_state(self, config: dict) -> GraphState:
        """Get current state from the latest checkpoint."""
        thread_id = config.get("thread_id", "default")
        checkpoint_config = CheckpointConfig(thread_id=thread_id)
        checkpoint = await self._checkpointer.get(checkpoint_config)
        if checkpoint:
            state = GraphState(checkpoint.values, schema=self._graph.schema)
            state.step = checkpoint.step
            return state
        return GraphState(schema=self._graph.schema)

    async def update_state(self, config: dict, values: dict) -> dict:
        """Update state by saving a new checkpoint."""
        thread_id = config.get("thread_id", "default")
        checkpoint_config = CheckpointConfig(thread_id=thread_id)
        existing = await self._checkpointer.get(checkpoint_config)
        state = GraphState(
            existing.values if existing else {},
            schema=self._graph.schema,
        )
        if existing:
            state.step = existing.step
        state.merge_update(values)
        checkpoint = Checkpoint(
            values=dict(state),
            next_nodes=list(existing.next_nodes) if existing else [],
            step=state.step,
            parent_id=existing.id if existing else None,
        )
        await self._checkpointer.put(checkpoint_config, checkpoint)
        return config

    async def resume_with(self, config: dict, value: Any) -> dict:
        """Resume from an interrupt with a human-provided value."""
        # Inject resume value into config so run() can apply it after checkpoint restore
        config = {**config, "__resume_value__": value}

        result = await self.run(GraphState(schema=self._graph.schema), config)
        return dict(result)

    async def _execute_super_step(
        self, state: GraphState, config: dict, context: ExecutionContext
    ) -> SuperStepResult:
        """Execute a single super-step: run all active nodes in parallel."""
        context.step += 1
        step = context.step
        active_nodes = list(context.active_nodes)
        logger.debug("super_step_start", step=step, active_nodes=active_nodes)

        tasks = []
        for node_name in active_nodes:
            if node_name in self._interrupt_before and node_name not in context.skip_interrupt_before:
                state["__interrupted__"] = True
                state["__interrupt_node__"] = node_name
                checkpoint = await self._save_checkpoint(
                    state, active_nodes, step, context, interrupt_type="before"
                )
                return SuperStepResult(
                    step=step,
                    active_nodes=active_nodes,
                    next_active=active_nodes,
                    interrupted=True,
                    checkpoint_id=checkpoint.id,
                )
            tasks.append(self._execute_node(node_name, state, config, context))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        node_results: dict[str, Any] = {}
        next_active: list[str] = []
        all_interrupted = False
        interrupt_node: str | None = None
        errors: dict[str, Exception] = {}

        for node_name, result in zip(active_nodes, results, strict=False):
            if isinstance(result, Exception):
                errors[node_name] = result
                logger.error("node_error", node=node_name, error=str(result), step=step)
                handler_result = await self._error_handler.handle(result, dict(state), node_name)
                if handler_result is None:
                    raise result
                self._merge_error_update(state, handler_result)
                continue

            node_results[node_name] = result

            # Route output to next nodes
            update, goto, resume = self._parse_output(result)
            if update:
                state.merge_update(update)
            if resume is not None:
                state["__resume_value__"] = resume

            next_nodes = await self._route_next(node_name, goto, state)
            next_active.extend(next_nodes)
            if is_command(result) and result.metadata.get("interrupt"):
                all_interrupted = True
                interrupt_node = node_name

        # Remove duplicates while preserving order
        seen: set[str] = set()
        unique_next: list[str] = []
        for n in next_active:
            if n not in seen and n != "__end__":
                seen.add(n)
                unique_next.append(n)

        if all_interrupted:
            state["__interrupted__"] = True
            state["__interrupt_node__"] = interrupt_node
        else:
            state["__interrupted__"] = False
            state.pop("__interrupt_node__", None)
        checkpoint = await self._save_checkpoint(
            state,
            unique_next,
            step,
            context,
            interrupt_type="after" if all_interrupted else None,
        )

        if self._debug:
            logger.debug(
                "super_step_complete",
                step=step,
                next_active=unique_next,
                checkpoint_id=checkpoint.id,
            )

        return SuperStepResult(
            step=step,
            node_results=node_results,
            active_nodes=active_nodes,
            next_active=unique_next,
            interrupted=all_interrupted,
            checkpoint_id=checkpoint.id,
            errors=errors,
        )

    @staticmethod
    def _merge_error_update(state: GraphState, update: dict[str, Any]) -> None:
        state.merge_update(update)
        state.update({key: value for key, value in update.items() if key.startswith("__")})

    async def _save_checkpoint(
        self,
        state: GraphState,
        next_nodes: list[str],
        step: int,
        context: ExecutionContext,
        interrupt_type: str | None = None,
    ) -> Checkpoint:
        metadata: dict[str, Any] = {"thread_id": context.thread_id}
        if interrupt_type:
            metadata.update({"interrupted": True, "interrupt_type": interrupt_type})
        checkpoint = Checkpoint(
            values=dict(state),
            next_nodes=next_nodes,
            step=step,
            parent_id=context.checkpoint_ids[-1] if context.checkpoint_ids else None,
            metadata=metadata,
        )
        await self._checkpointer.put(CheckpointConfig(thread_id=context.thread_id), checkpoint)
        context.checkpoint_ids.append(checkpoint.id)
        return checkpoint

    async def _execute_node(
        self, node_name: str, state: GraphState, config: dict, context: ExecutionContext
    ) -> Any:
        """Execute a single node with retry and timeout."""
        func = self._graph.get_node(node_name)
        if not func:
            raise ValueError(f"Node '{node_name}' not found in graph")

        state.current_node = node_name
        logger.debug("node_executing", node=node_name, step=context.step)

        try:
            execution = execute_with_retry(
                func,
                state,
                retry_policy=self._retry_policy,
                node_name=node_name,
            )
            if self._timeout_policy.node_timeout is None:
                result = await execution
            else:
                result = await asyncio.wait_for(execution, timeout=self._timeout_policy.node_timeout)

            if node_name in self._interrupt_after:
                if not is_command(result):
                    result = Command(update=result if isinstance(result, dict) else None, metadata={"interrupt": True})
                else:
                    result.metadata["interrupt"] = True

            return result

        except Exception as e:
            logger.error("node_failed", node=node_name, error=str(e))
            raise

    def _parse_output(self, output: Any) -> tuple[dict | None, str | list[str] | None, Any]:
        """Parse a node's output into update, goto, resume components."""
        return parse_node_output(output)

    async def _route_next(self, current_node: str, goto: str | list[str] | None, state: GraphState) -> list[str]:
        """Determine next nodes based on explicit goto or graph edges."""
        if goto is not None:
            if isinstance(goto, list):
                return [g for g in goto if g in self._graph.nodes or g == "__end__"]
            if goto in self._graph.nodes or goto == "__end__":
                return [goto]
            return []

        # Check conditional edges
        branch = self._graph.get_conditional_edges(current_node)
        if branch:
            next_node = await self._resolve_router(branch.router, state)
            if next_node in self._graph.nodes:
                return [next_node]
            return []

        # Use static edges
        outgoing = self._graph.get_outgoing_edges(current_node)
        return outgoing

    async def _resolve_router(self, router: callable, state: GraphState) -> str:
        """Resolve a router function to a node name."""
        try:
            result = router(state)
            if asyncio.iscoroutine(result) or asyncio.isfuture(result):
                result = await result
            return str(result)
        except Exception as e:
            logger.error("router_error", error=str(e))
            return "__end__"
