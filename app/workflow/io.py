"""Workflow import/export with versioning and format support."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel

from app.workflow import NodeType, Workflow, WorkflowEdge, WorkflowNode

logger = structlog.get_logger()

CURRENT_VERSION = "1.0.0"


class WorkflowValidationError(BaseModel):
    field: str
    message: str


class WorkflowImportResult(BaseModel):
    success: bool
    workflow: Workflow | None = None
    workflow_id: str | None = None
    errors: list[WorkflowValidationError] = []
    warnings: list[str] = []
    migrated: bool = False
    original_version: str | None = None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _serialize_workflow(workflow: Workflow) -> dict[str, Any]:
    return {
        "id": workflow.id,
        "name": workflow.name,
        "description": workflow.description or "",
        "nodes": [
            {
                "id": n.id,
                "type": n.type.value,
                "name": n.name,
                "config": n.config or {},
                "inputs": n.inputs or {},
            }
            for n in workflow.nodes
        ],
        "edges": [
            {
                "source": e.source,
                "target": e.target,
                "condition": e.condition or "",
            }
            for e in workflow.edges
        ],
    }


def _deserialize_workflow(data: dict[str, Any]) -> Workflow:
    metadata = data.get("metadata", {})
    nodes = [
        WorkflowNode(
            id=n.get("id", str(uuid.uuid4())[:8]),
            type=NodeType(n.get("type", "llm")),
            name=n.get("name", "node"),
            config=n.get("config", {}),
            inputs=n.get("inputs", {}),
        )
        for n in data.get("nodes", [])
    ]
    edges = [
        WorkflowEdge(
            source=e.get("source", ""),
            target=e.get("target", ""),
            condition=e.get("condition", ""),
        )
        for e in data.get("edges", [])
    ]
    return Workflow(
        id=data.get("id", str(uuid.uuid4())[:8]),
        name=metadata.get("name", "Imported Workflow"),
        description=metadata.get("description", ""),
        nodes=nodes,
        edges=edges,
    )


class WorkflowIO:
    @staticmethod
    def export_workflow(workflow: Workflow) -> dict[str, Any]:
        payload = {
            "version": CURRENT_VERSION,
            "exported_at": _now_iso(),
            "metadata": {
                "name": workflow.name,
                "description": workflow.description or "",
                "tags": getattr(workflow, "tags", []),
                "created_at": workflow.created_at.isoformat() if getattr(workflow, "created_at", None) else _now_iso(),
            },
            "nodes": _serialize_workflow(workflow)["nodes"],
            "edges": _serialize_workflow(workflow)["edges"],
        }
        return payload

    @staticmethod
    def export_to_file(workflow: Workflow, file_path: str | Path, fmt: str = "json") -> Path:
        data = WorkflowIO.export_workflow(workflow)
        path = Path(file_path)
        if fmt.lower() == "yaml":
            try:
                import yaml  # type: ignore[import-untyped]
                content = yaml.dump(data, allow_unicode=True, sort_keys=False)
            except ImportError:
                raise RuntimeError("PyYAML is required for YAML export. Install it with: pip install pyyaml") from None
        else:
            content = json.dumps(data, indent=2, ensure_ascii=False)
        path.write_text(content, encoding="utf-8")
        logger.info("workflow_exported_to_file", path=str(path), format=fmt, workflow_id=workflow.id)
        return path

    @staticmethod
    def validate_workflow(data: dict[str, Any]) -> WorkflowImportResult:
        errors: list[WorkflowValidationError] = []
        warnings: list[str] = []

        if not isinstance(data, dict):
            return WorkflowImportResult(success=False, errors=[WorkflowValidationError(field="root", message="Data must be a JSON object")])

        version = data.get("version")
        if not version:
            errors.append(WorkflowValidationError(field="version", message="Missing required field: version"))

        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        metadata = data.get("metadata", {})

        if not isinstance(nodes, list) or len(nodes) == 0:
            errors.append(WorkflowValidationError(field="nodes", message="nodes must be a non-empty array"))
        if not isinstance(edges, list):
            errors.append(WorkflowValidationError(field="edges", message="edges must be an array"))
        if not isinstance(metadata, dict):
            errors.append(WorkflowValidationError(field="metadata", message="metadata must be an object"))

        node_ids: set[str] = set()
        for i, node in enumerate(nodes):
            if not isinstance(node, dict):
                errors.append(WorkflowValidationError(field=f"nodes[{i}]", message="Each node must be an object"))
                continue
            nid = node.get("id")
            if not nid:
                errors.append(WorkflowValidationError(field=f"nodes[{i}].id", message="Node id is required"))
            elif nid in node_ids:
                errors.append(WorkflowValidationError(field=f"nodes[{i}].id", message=f"Duplicate node id: {nid}"))
            else:
                node_ids.add(nid)
            ntype = node.get("type")
            if ntype not in {t.value for t in NodeType}:
                errors.append(WorkflowValidationError(field=f"nodes[{i}].type", message=f"Unknown node type: {ntype}"))
            if not node.get("name"):
                warnings.append(f"Node {nid or i}: missing name")

        for i, edge in enumerate(edges):
            if not isinstance(edge, dict):
                errors.append(WorkflowValidationError(field=f"edges[{i}]", message="Each edge must be an object"))
                continue
            source = edge.get("source")
            target = edge.get("target")
            if source not in node_ids:
                errors.append(WorkflowValidationError(field=f"edges[{i}].source", message=f"Edge references unknown source node: {source}"))
            if target not in node_ids:
                errors.append(WorkflowValidationError(field=f"edges[{i}].target", message=f"Edge references unknown target node: {target}"))

        return WorkflowImportResult(
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            original_version=str(version) if version else None,
        )

    @staticmethod
    def _migrate(data: dict[str, Any], target_version: str = CURRENT_VERSION) -> tuple[dict[str, Any], bool]:
        version = str(data.get("version", "0.0.0"))
        if version == target_version:
            return data, False
        migrated = {
            "version": target_version,
            "exported_at": _now_iso(),
            "metadata": data.get("metadata", {}),
            "nodes": data.get("nodes", []),
            "edges": data.get("edges", []),
        }
        return migrated, True

    @staticmethod
    def import_workflow(data: dict[str, Any]) -> WorkflowImportResult:
        validation = WorkflowIO.validate_workflow(data)
        if not validation.success:
            return validation

        migrated_data, was_migrated = WorkflowIO._migrate(data)

        try:
            workflow = _deserialize_workflow(migrated_data)
        except Exception as e:
            return WorkflowImportResult(
                success=False,
                errors=[WorkflowValidationError(field="root", message=f"Failed to construct workflow: {e}")],
                original_version=validation.original_version,
                migrated=was_migrated,
            )

        return WorkflowImportResult(
            success=True,
            workflow=workflow,
            workflow_id=workflow.id,
            warnings=validation.warnings,
            migrated=was_migrated,
            original_version=validation.original_version,
        )
