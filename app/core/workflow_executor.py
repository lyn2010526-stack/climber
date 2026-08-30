"""Workflow executor with DAG topological sort for visual workflow execution.

This module provides the backend execution engine for workflows created
in the visual workflow editor. It converts React Flow nodes/edges into
the internal Workflow model and executes them via WorkflowEngine.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.core.agent_engine import AgentEngine
from app.core.di import resolve as di_resolve
from app.workflow import NodeType, Workflow, WorkflowEdge, WorkflowNode
from app.workflow.engine import WorkflowEngine
from app.workflow.registry import node_registry


def build_workflow_from_graph(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    name: str = "Visual Workflow",
) -> Workflow:
    """Convert React Flow graph data into a Workflow model.

    Parameters
    ----------
    nodes : list of dict
        Each dict has keys: id, type, data (dict with config)
    edges : list of dict
        Each dict has keys: source, target, sourceHandle, targetHandle
    name : str
        Workflow name

    Returns
    -------
    Workflow
    """
    workflow_nodes: list[WorkflowNode] = []
    for node in nodes:
        canvas_type = str(node.get("type", ""))
        runtime_type = node_registry.runtime_type(canvas_type)
        try:
            node_type: NodeType | str = NodeType(runtime_type)
        except ValueError:
            node_type = canvas_type
        data = node.get("data", {})

        config: dict[str, Any] = {}
        if node_type == NodeType.START:
            config = {
                "label": data.get("label", "Input"),
                "variable_name": data.get("variable_name", "input"),
                "required": data.get("required", "true") == "true",
            }
        elif node_type == NodeType.LLM:
            config = {
                "label": data.get("label", "LLM"),
                "model_id": data.get("model", "gpt-4"),
                "system_prompt": data.get("system_prompt", ""),
                "temperature": float(data.get("temperature", 0.7) or 0.7),
                "max_tokens": int(data.get("max_tokens", 2000) or 2000),
            }
        elif node_type == NodeType.TOOL:
            config = {
                "label": data.get("label", "Tool"),
                "tool_name": data.get("tool_name", ""),
                "tool_inputs": _parse_json_safe(data.get("parameters_(json)", "{}")),
            }
        elif node_type == NodeType.CONDITION:
            config = {
                "label": data.get("label", "Condition"),
                "variable": data.get("variable", ""),
                "operator": data.get("operator", "equals"),
                "value": data.get("expected_value", ""),
            }
        elif node_type == NodeType.END:
            config = {
                "label": data.get("label", "Output"),
                "format": data.get("format", "text"),
            }
        elif node_type == NodeType.ITERATOR:
            raw_max_iterations = data.get("max_iterations", 100)
            try:
                max_iterations = int(raw_max_iterations)
            except (TypeError, ValueError) as exc:
                raise ValueError("iterator max_iterations must be an integer") from exc
            if not 1 <= max_iterations <= 10_000:
                raise ValueError("iterator max_iterations must be between 1 and 10000")
            config = {
                "collection": data.get("collection", ""),
                "item_var": data.get("item_var", "item"),
                "max_iterations": max_iterations,
                "transform": data.get("transform", "item"),
            }
        else:
            config = dict(data.get("config") or data)
            config.pop("label", None)
            config.pop("executionStatus", None)
            config.pop("executionOutput", None)
            config.pop("executionError", None)

        workflow_nodes.append(WorkflowNode(
            id=node["id"],
            type=node_type,
            name=data.get("label", node.get("type", "node")),
            config=config,
        ))

    workflow_edges: list[WorkflowEdge] = []
    for edge in edges:
        source_handle = edge.get("sourceHandle") or ""
        # Map handle IDs to condition labels
        condition = ""
        if source_handle == "true":
            condition = "true"
        elif source_handle == "false":
            condition = "false"

        workflow_edges.append(WorkflowEdge(
            source=edge["source"],
            target=edge["target"],
            condition=condition,
            sourceHandle=source_handle,
            targetHandle=edge.get("targetHandle") or "",
        ))

    return Workflow(
        id=str(uuid4())[:8],
        name=name,
        description="Created in visual workflow editor",
        nodes=workflow_nodes,
        edges=workflow_edges,
    )


def _parse_json_safe(value: Any) -> dict[str, Any]:
    """Safely parse a JSON string, returning empty dict on failure."""
    import json
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        return json.loads(str(value))
    except (json.JSONDecodeError, TypeError):
        return {}


async def execute_visual_workflow(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    inputs: dict[str, str] | None = None,
    user_id: str = "system",
    engine: AgentEngine | None = None,
) -> dict[str, Any]:
    """Execute a workflow created from the visual editor.

    Parameters
    ----------
    nodes : list of dict
        React Flow nodes with id, type, data
    edges : list of dict
        React Flow edges with source, target
    inputs : dict, optional
        User inputs for the workflow
    user_id : str
        User ID for execution context
    engine : AgentEngine, optional
        Pre-existing engine instance

    Returns
    -------
    dict
        Execution result with status, outputs, and node results
    """
    validation = validate_workflow_graph(nodes, edges)
    if not validation["valid"]:
        raise ValueError("Invalid workflow graph: " + "; ".join(validation["errors"]))

    if engine is None:
        from app.tools import tool_registry
        model_registry = di_resolve("ModelRegistry")
        engine = AgentEngine(
            model_registry=model_registry,
            tool_registry=tool_registry,
        )

    workflow = build_workflow_from_graph(nodes, edges)
    wf_engine = WorkflowEngine(engine)
    result = await wf_engine.execute(workflow, user_inputs=inputs, user_id=user_id)

    return result.model_dump()


def validate_workflow_graph(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate a workflow graph before execution.

    Checks:
    - Has at least one input and one output node
    - No cycles (except via condition branches)
    - All edges reference existing nodes
    - Required node configs are present
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(nodes, list):
        raise ValueError("nodes must be an array")
    if not isinstance(edges, list):
        raise ValueError("edges must be an array")
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise ValueError(f"nodes[{index}] must be an object")
        if not isinstance(node.get("id"), str) or not node["id"].strip():
            raise ValueError(f"nodes[{index}].id is required")
        if "data" in node and not isinstance(node["data"], dict):
            raise ValueError(f"nodes[{index}].data must be an object")
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            raise ValueError(f"edges[{index}] must be an object")
        for field in ("source", "target"):
            if not isinstance(edge.get(field), str) or not edge[field].strip():
                raise ValueError(f"edges[{index}].{field} must be a string")
        for field in ("sourceHandle", "targetHandle"):
            if edge.get(field) is not None and not isinstance(edge[field], str):
                raise ValueError(f"edges[{index}].{field} must be a string")

    node_ids = {n["id"] for n in nodes}

    # Check for input and output nodes
    has_input = any(n.get("type") == "input" for n in nodes)
    has_output = any(n.get("type") == "output" for n in nodes)

    if not has_input:
        errors.append("Workflow must have at least one Input node")
    if not has_output:
        errors.append("Workflow must have at least one Output node")

    # Check edges reference valid nodes
    nodes_by_id = {node["id"]: node for node in nodes}
    for edge in edges:
        if edge.get("source") not in node_ids:
            errors.append(f"Edge references unknown source node: {edge.get('source')}")
        if edge.get("target") not in node_ids:
            errors.append(f"Edge references unknown target node: {edge.get('target')}")
        source_handle = edge.get("sourceHandle", "")
        target_handle = edge.get("targetHandle", "")
        if source_handle and target_handle:
            source_node = nodes_by_id.get(edge.get("source"))
            target_node = nodes_by_id.get(edge.get("target"))
            if source_node and target_node:
                compatibility_error = node_registry.check_connection(
                    str(source_node.get("type", "")),
                    source_handle,
                    str(target_node.get("type", "")),
                    target_handle,
                )
                if compatibility_error:
                    errors.append(compatibility_error)

    # Check for disconnected nodes
    connected_ids: set[str] = set()
    for edge in edges:
        connected_ids.add(edge.get("source", ""))
        connected_ids.add(edge.get("target", ""))
    disconnected = node_ids - connected_ids
    if disconnected:
        warnings.append(f"Disconnected nodes found: {', '.join(disconnected)}")

    # Check required configs
    for node in nodes:
        node_type = node.get("type", "")
        data = node.get("data", {})
        if node_type == "llm" and not data.get("model"):
            warnings.append(f"Node {node['id']}: No model selected")
        if node_type == "tool" and not data.get("tool_name"):
            warnings.append(f"Node {node['id']}: No tool selected")
        if node_type == "condition" and not data.get("variable"):
            warnings.append(f"Node {node['id']}: No variable specified")

    # Detect cycles via topological sort
    try:
        workflow = build_workflow_from_graph(nodes, edges)
    except (TypeError, ValueError) as e:
        errors.append(f"Invalid workflow graph: {e}")
    else:
        try:
            workflow.topological_sort()
        except ValueError as e:
            errors.append(f"Cycle detected: {e}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }
