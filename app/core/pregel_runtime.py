"""Pregel workflow runtime adapter for AgentEngine.

Wraps the PregelEngine into a workflow runtime with checkpoint persistence,
predefined workflows, and singleton access.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any

import structlog

from app.core.engine.pregel import (
    Command,
    InMemoryCheckpointSaver,
    PregelEngine,
    SqliteCheckpointSaver,
    StateGraph,
)

logger = structlog.get_logger(__name__)

CHECKPOINT_DB_PATH = "/workspace/agent-engine/data/pregel_checkpoints.db"
MAX_RETRIES = 2

NodeFunc = Callable[[dict], Any]


async def _analyze_agent_node(state: dict) -> dict:
    prompt = state.get("prompt", "")
    return {"agent_response": f"received: {prompt}"}


async def _analyze_analysis_node(state: dict) -> dict:
    response = state.get("agent_response", "")
    return {"analysis": f"analysis of {response}"}


async def _analyze_summary_node(state: dict) -> dict:
    analysis = state.get("analysis", "")
    return {"summary": f"summary: {analysis}"}


async def _retry_process_node(state: dict) -> dict:
    attempts = int(state.get("attempts", 0))
    fail_until = int(state.get("fail_until", 0))
    payload = state.get("payload", "")
    if attempts < fail_until:
        return {"status": "failed", "error": f"simulated failure at attempt {attempts + 1}"}
    return {"status": "success", "result": f"processed: {payload}"}


async def _retry_router(state: dict) -> str:
    if state.get("status") == "success":
        return "complete"
    return "retry"


async def _retry_retry_node(state: dict) -> Command:
    attempts = int(state.get("attempts", 0)) + 1
    if attempts > MAX_RETRIES:
        return Command(update={"attempts": attempts, "status": "failed"}, goto="fail")
    return Command(update={"attempts": attempts}, goto="process")


async def _retry_complete_node(state: dict) -> dict:
    return {"final_status": "complete", "result": state.get("result", "")}


async def _retry_fail_node(state: dict) -> dict:
    return {"final_status": "failed", "error": state.get("error", "")}


def _build_checkpointer() -> InMemoryCheckpointSaver | SqliteCheckpointSaver:
    try:
        os.makedirs(os.path.dirname(CHECKPOINT_DB_PATH), exist_ok=True)
        return SqliteCheckpointSaver(CHECKPOINT_DB_PATH)
    except Exception as exc:
        logger.warning("checkpoint_saver_fallback", error=str(exc), backend="InMemoryCheckpointSaver")
        return InMemoryCheckpointSaver()


class PregelWorkflowRuntime:
    """Workflow runtime that builds and runs StateGraphs on the PregelEngine."""

    def __init__(self) -> None:
        self._checkpointer: InMemoryCheckpointSaver | SqliteCheckpointSaver = _build_checkpointer()
        self._workflows: dict[str, dict[str, Any]] = {}
        self._register_default_workflows()

    def _register_default_workflows(self) -> None:
        self.register_workflow(
            name="analyze",
            nodes={
                "agent": _analyze_agent_node,
                "analyze": _analyze_analysis_node,
                "summarize": _analyze_summary_node,
            },
            edges=[("agent", "analyze"), ("analyze", "summarize")],
            entry_point="agent",
        )
        self.register_workflow(
            name="retry_pipeline",
            nodes={
                "process": _retry_process_node,
                "retry": _retry_retry_node,
                "complete": _retry_complete_node,
                "fail": _retry_fail_node,
            },
            edges=[
                (
                    "process",
                    {"router": _retry_router, "path_map": {"complete": "complete", "retry": "retry"}},
                )
            ],
            entry_point="process",
        )

    def register_workflow(
        self,
        name: str,
        nodes: dict[str, NodeFunc],
        edges: list[tuple[str, str | dict[str, Any]]],
        entry_point: str,
    ) -> None:
        """Register a workflow definition for later execution."""
        self._workflows[name] = {
            "nodes": dict(nodes),
            "edges": list(edges),
            "entry_point": entry_point,
        }
        logger.info("workflow_registered", workflow=name, nodes=list(nodes))

    def _build_graph(self, workflow_name: str) -> StateGraph:
        spec = self._workflows.get(workflow_name)
        if spec is None:
            raise ValueError(f"Unknown workflow '{workflow_name}'")
        graph = StateGraph()
        for node_name, node_func in spec["nodes"].items():
            graph.add_node(node_name, node_func)
        for src, dst in spec["edges"]:
            if isinstance(dst, dict):
                graph.add_conditional_edges(src, dst["router"], dst.get("path_map"))
            else:
                graph.add_edge(src, dst)
        graph.set_entry_point(spec["entry_point"])
        return graph

    async def execute_workflow(
        self,
        workflow_name: str,
        inputs: dict[str, Any],
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        """Build and run a workflow to completion, returning the final state."""
        graph = self._build_graph(workflow_name)
        app = graph.compile(checkpointer=self._checkpointer)
        config = {"thread_id": thread_id or str(uuid.uuid4())}
        logger.info("workflow_execute_start", workflow=workflow_name, thread_id=config["thread_id"])
        result = await app.invoke(inputs, config)
        logger.info("workflow_execute_end", workflow=workflow_name, thread_id=config["thread_id"])
        return dict(result)

    async def stream_workflow(
        self,
        workflow_name: str,
        inputs: dict[str, Any],
        thread_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream state updates for a workflow after each super-step."""
        graph = self._build_graph(workflow_name)
        app = graph.compile(checkpointer=self._checkpointer)
        config = {"thread_id": thread_id or str(uuid.uuid4())}
        logger.info("workflow_stream_start", workflow=workflow_name, thread_id=config["thread_id"])
        async for step_state in app.astream(inputs, config):
            yield dict(step_state)


_runtime_instance: PregelWorkflowRuntime | None = None
_runtime_lock = asyncio.Lock()


async def get_runtime() -> PregelWorkflowRuntime:
    """Return the singleton PregelWorkflowRuntime instance."""
    global _runtime_instance
    if _runtime_instance is None:
        async with _runtime_lock:
            if _runtime_instance is None:
                _runtime_instance = PregelWorkflowRuntime()
    return _runtime_instance
