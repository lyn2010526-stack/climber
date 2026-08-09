"""Pregel-style superstep execution engine.

"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from app.core.state_graph import StateGraph

logger = logging.getLogger(__name__)


@dataclass
class PendingWrite:
    channel: str
    value: Any
    write_id: str
    status: str = "pending"  # pending / committed / rolled_back


@dataclass
class Checkpoint:
    thread_id: str
    step: int
    channel_values: dict[str, Any]
    channel_versions: dict[str, int]
    versions_seen: dict[str, dict[str, int]]
    pending_writes: list[PendingWrite]
    metadata: dict[str, Any] = field(default_factory=dict)


class PregelLoop:
    """Superstep execution engine for StateGraph.

    Features:
    - Parallel execution of ready nodes per superstep
    - Channel-based state aggregation
    - Checkpoint save/restore
    - Dynamic routing via Command
    """

    def __init__(self, graph: StateGraph, checkpoint_store: Any | None = None):
        self.graph = graph
        self.checkpoint_store = checkpoint_store
        self._running = False

    async def execute(self, thread_id: str, inputs: dict[str, Any], max_steps: int = 100) -> dict[str, Any]:
        """Execute the state graph.

        Args:
            thread_id: Unique thread/session identifier
            inputs: Initial channel values
            max_steps: Maximum supersteps to prevent infinite loops

        Returns:
            Final channel values
        """
        # Initialize channels with inputs
        for key, value in inputs.items():
            self.graph.set_channel(key, value)

        # Track which nodes have been visited
        visited: set[str] = set()
        current_step = 0

        # Load checkpoint if exists
        if self.checkpoint_store and thread_id:
            checkpoint = await self.checkpoint_store.get(thread_id)
            if checkpoint:
                logger.info("resuming_from_checkpoint", thread_id=thread_id, step=checkpoint.step)
                for key, value in checkpoint.channel_values.items():
                    self.graph.set_channel(key, value)
                visited = set(checkpoint.versions_seen.get("nodes", {}).keys())
                current_step = checkpoint.step

        self._running = True
        try:
            while current_step < max_steps:
                # Determine ready nodes (all incoming edges satisfied)
                ready = self._get_ready_nodes(visited)
                if not ready:
                    logger.info("no_ready_nodes", step=current_step)
                    break

                # Execute ready nodes in parallel
                tasks = []
                for node_name in ready:
                    tasks.append(self._execute_node(node_name, thread_id))

                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results and update channels
                for node_name, result in zip(ready, results):
                    if isinstance(result, Exception):
                        logger.error("node_failed", node=node_name, error=str(result))
                        continue
                    if result is not None:
                        if isinstance(result, dict):
                            for key, value in result.items():
                                self.graph.set_channel(key, value)
                        elif isinstance(result, str) and result.startswith("goto:"):
                            target = result[5:]
                            visited.add(target)

                visited.update(ready)
                current_step += 1

                # Save checkpoint
                if self.checkpoint_store and thread_id:
                    checkpoint = Checkpoint(
                        thread_id=thread_id,
                        step=current_step,
                        channel_values={k: v.get() if hasattr(v, "get") else v for k, v in self.graph.channels.items()},
                        channel_versions={k: current_step for k in self.graph.channels},
                        versions_seen={"nodes": {n: current_step for n in visited}},
                        pending_writes=[],
                        metadata={"current_step": current_step},
                    )
                    await self.checkpoint_store.put(thread_id, checkpoint)

        finally:
            self._running = False

        return {k: v.get() if hasattr(v, "get") else v for k, v in self.graph.channels.items()}

    def _get_ready_nodes(self, visited: set[str]) -> list[str]:
        """Get nodes whose dependencies are satisfied."""
        ready = []
        for node_name in self.graph.nodes:
            if node_name in visited:
                continue
            # Check if all incoming edges are from visited nodes
            deps_met = all(
                edge.source in visited
                for edge in self.graph.edges
                if (edge.target == node_name or (isinstance(edge.target, list) and node_name in edge.target))
            )
            if deps_met:
                ready.append(node_name)
        return ready

    async def _execute_node(self, node_name: str, thread_id: str) -> Any:
        """Execute a single node."""
        spec = self.graph.nodes.get(node_name)
        if not spec:
            return None

        logger.debug("executing_node", node=node_name)
        try:
            if asyncio.iscoroutinefunction(spec.func):
                result = await asyncio.wait_for(spec.func(self.graph, thread_id), timeout=spec.timeout)
            else:
                result = spec.func(self.graph, thread_id)
            return result
        except asyncio.TimeoutError:
            logger.error("node_timeout", node=node_name)
            if spec.on_error:
                return spec.on_error(node_name, None)
            return None
        except Exception as e:
            logger.error("node_error", node=node_name, error=str(e))
            if spec.on_error:
                return spec.on_error(node_name, e)
            return None
