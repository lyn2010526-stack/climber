"""Pregel workflow facade: execute visual workflow graphs with Pregel.

The facade keeps the existing ``WorkflowEngine`` node semantics while
replacing the DAG topological executor with the compiled Pregel runtime.
Callers may opt in through ``pregel=True`` on workflow runs; the previous
executor remains the default to avoid changing API behavior.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from app.core.agent_engine import AgentEngine
from app.core.engine.pregel.graph import StateGraph
from app.core.engine.pregel.policies import DefaultErrorHandler, RetryPolicy
from app.core.workflow_executor import build_workflow_from_graph
from app.workflow import NodeType, Workflow, WorkflowNode
from app.workflow.engine import WorkflowEngine

NodeExecutor = Callable[[WorkflowNode, dict[str, Any]], Any]


class PregelWorkflowAdapter:
    """Compile and run a visual workflow graph on the Pregel runtime.

    The adapter keeps ``WorkflowEngine`` as the node executor so LLM, tool,
    simulation, code, and condition nodes keep their existing semantics.
    """

    def __init__(
        self,
        engine: AgentEngine,
        model_registry: Any = None,
        tool_registry: Any = None,
        node_executor: Callable[[WorkflowNode, dict[str, Any]], Any] | None = None,
    ) -> None:
        self.agent_engine = engine
        self.workflow_engine = WorkflowEngine(
            engine,
            model_registry=model_registry,
            tool_registry=tool_registry,
        )
        self._node_executor = node_executor

    def compile(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        name: str = "Pregel Workflow",
        user_id: str = "system",
    ) -> tuple[StateGraph, Workflow]:
        """Build a Pregel StateGraph from visual workflow data.

        Returns:
            A tuple of the compiled graph builder and the parsed Workflow.
        """
        workflow = build_workflow_from_graph(nodes, edges, name=name)
        graph = StateGraph()

        entry = self._entry_node(workflow)
        graph.set_entry_point("__start__")
        graph.add_node("__start__", self._make_start_node(workflow, entry.id))
        graph.add_edge("__start__", entry.id)

        for node in workflow.nodes:
            graph.add_node(node.id, self._make_workflow_node(node, workflow, user_id))

        self._add_edges(graph, workflow)
        return graph, workflow

    async def run(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        inputs: dict[str, Any] | None = None,
        name: str = "Pregel Workflow",
        user_id: str = "system",
    ) -> dict[str, Any]:
        """Compile and execute a visual workflow graph.

        Returns:
            A dictionary with status, outputs, node_results, and duration.
        """
        inputs = inputs or {}
        started = time.perf_counter()
        graph, workflow = self.compile(nodes, edges, name=name, user_id=user_id)
        compiled = graph.compile(
            retry_policy=RetryPolicy(max_attempts=1),
            error_handler=DefaultErrorHandler(continue_on_error=False),
        )

        try:
            final_state = await compiled.invoke({"__start__": inputs})
            outputs = self._collect_outputs(workflow, final_state)
            node_results = self._collect_node_results(workflow, final_state)
            return {
                "id": workflow.id,
                "status": "completed",
                "outputs": outputs,
                "node_results": node_results,
                "execution_time_ms": (time.perf_counter() - started) * 1000,
                "error": "",
            }
        except Exception as exc:
            return {
                "id": workflow.id,
                "status": "failed",
                "outputs": {},
                "node_results": {},
                "execution_time_ms": (time.perf_counter() - started) * 1000,
                "error": str(exc),
            }

    def _entry_node(self, workflow: Workflow) -> WorkflowNode:
        """Pick the graph entry: START when present, else a source node."""
        start = next((n for n in workflow.nodes if n.type == NodeType.START), None)
        if start is not None:
            return start
        sources = self._source_nodes(workflow)
        return next((n for n in workflow.nodes if n.id in sources), workflow.nodes[0])

    @staticmethod
    def _source_nodes(workflow: Workflow) -> set[str]:
        targets = {e.target for e in workflow.edges}
        return {n.id for n in workflow.nodes if n.id not in targets}

    def _make_start_node(self, workflow: Workflow, entry_id: str):
        """Return a node that seeds user inputs into Pregel state."""

        async def start(state: dict[str, Any]) -> dict[str, Any]:
            inputs = state.get("__start__", {})
            return {"_inputs": inputs, entry_id: inputs}

        return start

    def _make_workflow_node(self, node: WorkflowNode, workflow: Workflow, user_id: str):
        """Return an async Pregel node bound to the WorkflowEngine executor."""

        async def run_node(state: dict[str, Any]) -> dict[str, Any]:
            if node.type == NodeType.START:
                return {}
            resolved = self._resolve_inputs(node, workflow, state)
            if self._node_executor is not None:
                if node.type == NodeType.END:
                    resolved = {**state.get("_inputs", {}), **resolved}
                output = self._node_executor(node, resolved)
                if asyncio.iscoroutine(output):
                    output = await output
            elif node.type == NodeType.END:
                output = resolved
            elif node.type == NodeType.CONDITION:
                output = self.workflow_engine._execute_condition_node(node, resolved)
            elif node.type == NodeType.LLM:
                output = await self.workflow_engine._execute_llm_node(node, resolved, user_id)
            elif node.type == NodeType.TOOL:
                output = await self.workflow_engine._execute_tool_node(node, resolved)
            elif node.type == NodeType.CODE:
                output = await self.workflow_engine._execute_code_node(node, resolved)
            elif node.type == NodeType.SIMULATION:
                output = await self.workflow_engine._execute_simulation_node(node, resolved)
            elif node.type == NodeType.ITERATOR:
                output = await self.workflow_engine._execute_iterator_node(node, resolved, user_id, set())
            else:
                output = resolved
            return {node.id: output}

        run_node.__pregel_node_id__ = node.id
        return run_node

    def _add_edges(self, graph: StateGraph, workflow: Workflow) -> None:
        """Register normal and conditional edges on the Pregel graph."""
        grouped = defaultdict(list)
        for edge in workflow.edges:
            grouped[edge.source].append(edge)

        for source, outgoing in grouped.items():
            condition_node = next(
                (n for n in workflow.nodes if n.id == source and n.type == NodeType.CONDITION),
                None,
            )
            if condition_node is not None:
                graph.add_conditional_edges(
                    source,
                    self._condition_router(source, workflow),
                    self._condition_path_map(source, workflow),
                )
            for edge in outgoing:
                if not edge.condition:
                    graph.add_edge(source, edge.target)

        for node in workflow.nodes:
            if not any(edge.source == node.id for edge in workflow.edges):
                graph.add_edge(node.id, "__end__")

    def _condition_router(self, node_id: str, workflow: Workflow):
        """Return a router reading a condition node's boolean result."""

        async def router(state: dict[str, Any]) -> str:
            output = state.get(node_id, {})
            if isinstance(output, dict):
                result = output.get("condition_result", False)
            else:
                result = bool(output)
            return "true" if result else "false"

        return router

    @staticmethod
    def _condition_path_map(source: str, workflow: Workflow) -> dict[str, str]:
        path_map: dict[str, str] = {}
        for edge in workflow.get_successors(source):
            if edge.condition in {"true", "false"}:
                path_map[edge.condition] = edge.target
        return path_map

    def _resolve_inputs(
        self,
        node: WorkflowNode,
        workflow: Workflow,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge predecessor outputs from Pregel state."""
        resolved: dict[str, Any] = {}
        for pred_id in workflow.get_predecessors(node.id):
            output = state.get(pred_id)
            if output is None:
                continue
            if isinstance(output, dict):
                for k, v in output.items():
                    resolved[k] = v
            else:
                resolved[pred_id] = output

        for key, ref in node.inputs.items():
            if "." in ref:
                node_id, output_key = ref.split(".", 1)
            else:
                node_id = ref
                output_key = None
            output = state.get(node_id)
            if output is None:
                continue
            if output_key:
                resolved[key] = output.get(output_key) if isinstance(output, dict) else output
            else:
                resolved[key] = output.get("result", output) if isinstance(output, dict) else output
        return resolved

    def _collect_outputs(
        self,
        workflow: Workflow,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        end_nodes = [n for n in workflow.nodes if n.type == NodeType.END]
        if end_nodes:
            outputs: dict[str, Any] = {}
            for node in end_nodes:
                outputs[node.name] = state.get(node.id, {})
            return outputs
        completed = [
            (n, state.get(n.id))
            for n in workflow.nodes
            if n.type != NodeType.START and state.get(n.id) is not None
        ]
        if completed:
            last_node, last_output = completed[-1]
            return {"result": last_output, "node": last_node.name}
        return {}

    def _collect_node_results(
        self,
        workflow: Workflow,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for node in workflow.nodes:
            output = state.get(node.id)
            if output is not None:
                results[node.id] = {
                    "name": node.name,
                    "type": node.type.value,
                    "output": output,
                    "status": "completed",
                }
        return results
