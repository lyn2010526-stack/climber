"""Workflow engine with DAG execution (Dify style)."""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    START = "start"
    LLM = "llm"
    TOOL = "tool"
    CONDITION = "condition"
    CODE = "code"
    ITERATOR = "iterator"
    END = "end"


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowNode(BaseModel):
    """A single node in the workflow DAG."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: NodeType
    name: str
    config: dict[str, Any] = Field(default_factory=dict)
    inputs: dict[str, str] = Field(default_factory=dict)
    status: NodeStatus = NodeStatus.PENDING
    output: Any = None
    error: str = ""


class WorkflowEdge(BaseModel):
    """A directed edge between two nodes."""

    source: str
    target: str
    condition: str = ""  # For conditional branching


class Workflow(BaseModel):
    """A DAG-based workflow definition."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    description: str = ""
    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[WorkflowEdge] = Field(default_factory=list)

    def get_node(self, node_id: str) -> WorkflowNode | None:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def get_predecessors(self, node_id: str) -> list[str]:
        return [e.source for e in self.edges if e.target == node_id]

    def get_successors(self, node_id: str) -> list[WorkflowEdge]:
        return [e for e in self.edges if e.source == node_id]

    def topological_sort(self) -> list[list[str]]:
        """Return layers of node IDs that can be executed in parallel."""
        in_degree: dict[str, int] = {n.id: 0 for n in self.nodes}
        for edge in self.edges:
            in_degree[edge.target] = in_degree.get(edge.target, 0) + 1

        layers: list[list[str]] = []
        remaining = set(n.id for n in self.nodes)

        while remaining:
            layer = [nid for nid in remaining if in_degree.get(nid, 0) == 0]
            if not layer:
                raise ValueError("Cycle detected in workflow DAG")
            layers.append(layer)
            for nid in layer:
                remaining.remove(nid)
                for edge in self.get_successors(nid):
                    in_degree[edge.target] -= 1

        return layers


class WorkflowResult(BaseModel):
    """Result of a workflow execution."""

    workflow_id: str
    status: str
    outputs: dict[str, Any] = Field(default_factory=dict)
    node_results: dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: float = 0
    error: str = ""
