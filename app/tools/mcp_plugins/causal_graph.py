"""MCP Plugin: Causal Graph — event causality knowledge graph.

Builds causal relationships between events to support root cause
analysis and "why did this fail" reasoning.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CausalNode:
    id: str
    description: str
    node_type: str  # "action", "outcome", "goal", "error"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalEdge:
    source: str
    target: str
    relation: str  # "causes", "precedes", "contributes_to", "blocks"
    strength: float = 1.0  # 0.0-1.0


class CausalGraph:
    """Causal knowledge graph for event relationship tracking."""

    def __init__(self, storage_path: str = "data/causal_graph.json"):
        self._storage_path = storage_path
        self._nodes: dict[str, CausalNode] = {}
        self._edges: list[CausalEdge] = []
        self._load()

    def add_event(
        self,
        event_id: str,
        description: str,
        node_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> CausalNode:
        node = CausalNode(
            id=event_id,
            description=description,
            node_type=node_type,
            metadata=metadata or {},
        )
        self._nodes[event_id] = node
        return node

    def add_causality(
        self,
        source_id: str,
        target_id: str,
        relation: str = "causes",
        strength: float = 1.0,
    ) -> bool:
        if source_id not in self._nodes or target_id not in self._nodes:
            return False
        self._edges.append(CausalEdge(
            source=source_id,
            target=target_id,
            relation=relation,
            strength=strength,
        ))
        return True

    def find_root_causes(self, event_id: str) -> list[CausalNode]:
        """Trace back to find root causes of an event."""
        roots = []
        visited = set()
        self._trace_back(event_id, roots, visited)
        return roots

    def _trace_back(
        self,
        event_id: str,
        roots: list[CausalNode],
        visited: set[str],
    ) -> None:
        if event_id in visited:
            return
        visited.add(event_id)

        predecessors = [
            e for e in self._edges if e.target == event_id
        ]
        if not predecessors:
            if event_id in self._nodes:
                roots.append(self._nodes[event_id])
            return

        for edge in predecessors:
            self._trace_back(edge.source, roots, visited)

    def find_effects(self, event_id: str) -> list[CausalNode]:
        """Find all downstream effects of an event."""
        effects = []
        visited = set()
        self._trace_forward(event_id, effects, visited)
        return effects

    def _trace_forward(
        self,
        event_id: str,
        effects: list[CausalNode],
        visited: set[str],
    ) -> None:
        if event_id in visited:
            return
        visited.add(event_id)

        successors = [
            e for e in self._edges if e.source == event_id
        ]
        for edge in successors:
            if edge.target in self._nodes:
                effects.append(self._nodes[edge.target])
            self._trace_forward(edge.target, effects, visited)

    def explain_failure(self, failure_event_id: str) -> dict[str, Any]:
        """Build a failure explanation chain."""
        root_causes = self.find_root_causes(failure_event_id)
        failure_node = self._nodes.get(failure_event_id)

        return {
            "failure": failure_node.description if failure_node else failure_event_id,
            "root_causes": [
                {"id": n.id, "description": n.description, "type": n.node_type}
                for n in root_causes
            ],
            "chain_length": len(root_causes),
        }

    def get_graph_stats(self) -> dict[str, int]:
        return {
            "nodes": len(self._nodes),
            "edges": len(self._edges),
        }

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "causal_add_event",
                "description": "Add an event node to the causal graph",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_id": {"type": "string"},
                        "description": {"type": "string"},
                        "node_type": {
                            "type": "string",
                            "enum": ["action", "outcome", "goal", "error"],
                        },
                    },
                    "required": ["event_id", "description", "node_type"],
                },
            },
            {
                "name": "causal_link",
                "description": "Create a causal link between two events",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source_id": {"type": "string"},
                        "target_id": {"type": "string"},
                        "relation": {
                            "type": "string",
                            "enum": ["causes", "precedes", "contributes_to", "blocks"],
                        },
                        "strength": {"type": "number"},
                    },
                    "required": ["source_id", "target_id"],
                },
            },
            {
                "name": "causal_explain",
                "description": "Explain why a failure occurred by tracing root causes",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_id": {"type": "string"},
                    },
                    "required": ["event_id"],
                },
            },
        ]

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)
        data = {
            "nodes": {
                nid: {
                    "id": n.id,
                    "description": n.description,
                    "node_type": n.node_type,
                    "metadata": n.metadata,
                }
                for nid, n in self._nodes.items()
            },
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "relation": e.relation,
                    "strength": e.strength,
                }
                for e in self._edges
            ],
        }
        with open(self._storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self) -> None:
        if not os.path.exists(self._storage_path):
            return
        try:
            with open(self._storage_path) as f:
                data = json.load(f)
            for nid, n in data.get("nodes", {}).items():
                self._nodes[nid] = CausalNode(
                    id=n["id"],
                    description=n["description"],
                    node_type=n["node_type"],
                    metadata=n.get("metadata", {}),
                )
            for e in data.get("edges", []):
                self._edges.append(CausalEdge(
                    source=e["source"],
                    target=e["target"],
                    relation=e["relation"],
                    strength=e.get("strength", 1.0),
                ))
        except (json.JSONDecodeError, KeyError):
            pass
