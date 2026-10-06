"""Coverage tests for app/workflow/io.py (import/export/validation/migration)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.workflow import NodeType, Workflow, WorkflowEdge, WorkflowNode
from app.workflow.io import (
    CURRENT_VERSION,
    WorkflowIO,
    WorkflowValidationError,
    _deserialize_workflow,
)


def _valid_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "version": CURRENT_VERSION,
        "metadata": {"name": "My Flow", "description": "desc"},
        "nodes": [
            {"id": "start", "type": "start", "name": "Start"},
            {"id": "end", "type": "end", "name": "End"},
        ],
        "edges": [{"source": "start", "target": "end"}],
    }
    data.update(overrides)
    return data


def _workflow() -> Workflow:
    return Workflow(
        id="wf-1",
        name="Demo",
        description="A demo workflow",
        nodes=[
            WorkflowNode(
                id="n1",
                type=NodeType.LLM,
                name="LLM",
                config={"prompt": "hi"},
                inputs={"x": "y"},
            )
        ],
        edges=[WorkflowEdge(source="n1", target="n1", condition="ok")],
    )


# ── export ────────────────────────────────────────────────────────────────


def test_export_workflow_uses_current_version() -> None:
    data = WorkflowIO.export_workflow(_workflow())
    assert data["version"] == CURRENT_VERSION
    assert data["metadata"]["name"] == "Demo"
    assert data["metadata"]["description"] == "A demo workflow"
    assert data["metadata"]["tags"] == []
    # Workflow has no created_at -> fallback to _now_iso()
    assert isinstance(data["metadata"]["created_at"], str)
    assert data["nodes"][0]["config"] == {"prompt": "hi"}
    assert data["edges"][0]["condition"] == "ok"


def test_export_workflow_with_extra_attrs() -> None:
    created = datetime(2024, 1, 2, 3, 4, 5, tzinfo=UTC)
    workflow = SimpleNamespace(
        id="wf-2",
        name="Extra",
        description=None,
        nodes=[],
        edges=[],
        created_at=created,
        tags=["a", "b"],
    )
    data = WorkflowIO.export_workflow(workflow)  # type: ignore[arg-type]
    assert data["metadata"]["description"] == ""
    assert data["metadata"]["tags"] == ["a", "b"]
    assert data["metadata"]["created_at"] == created.isoformat()


def test_export_to_file_json(tmp_path) -> None:
    path = WorkflowIO.export_to_file(_workflow(), tmp_path / "wf.json")
    assert path.exists()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["version"] == CURRENT_VERSION


def test_export_to_file_yaml(tmp_path) -> None:
    path = WorkflowIO.export_to_file(_workflow(), tmp_path / "wf.yaml", fmt="YAML")
    content = path.read_text(encoding="utf-8")
    assert "version:" in content


def test_export_to_file_yaml_missing_pyyaml(tmp_path, monkeypatch) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "yaml":
            raise ImportError("no yaml")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(RuntimeError, match="PyYAML is required"):
        WorkflowIO.export_to_file(_workflow(), tmp_path / "wf.yaml", fmt="yaml")


# ── validate ──────────────────────────────────────────────────────────────


def test_validate_root_not_dict() -> None:
    result = WorkflowIO.validate_workflow("nope")  # type: ignore[arg-type]
    assert result.success is False
    assert result.errors[0].field == "root"


def test_validate_valid() -> None:
    result = WorkflowIO.validate_workflow(_valid_data())
    assert result.success is True
    assert result.errors == []
    assert result.original_version == CURRENT_VERSION


def test_validate_missing_version_and_nodes() -> None:
    result = WorkflowIO.validate_workflow({"nodes": [], "edges": []})
    fields = {e.field for e in result.errors}
    assert "version" in fields
    assert "nodes" in fields


def test_validate_edges_and_metadata_wrong_type() -> None:
    result = WorkflowIO.validate_workflow(
        {
            "version": "1.0.0",
            "nodes": [{"id": "n", "type": "llm", "name": "N"}],
            "edges": "bad",
            "metadata": [1, 2],
        }
    )
    fields = {e.field for e in result.errors}
    assert "edges" in fields
    assert "metadata" in fields


def test_validate_node_errors() -> None:
    data = _valid_data(
        nodes=[
            "not-a-dict",
            {"type": "llm", "name": "NoId"},
            {"id": "dup", "type": "llm", "name": "A"},
            {"id": "dup", "type": "llm", "name": "B"},
            {"id": "badtype", "type": "does-not-exist", "name": "C"},
            {"id": "noname", "type": "llm"},
        ]
    )
    result = WorkflowIO.validate_workflow(data)
    assert result.success is False
    fields = [e.field for e in result.errors]
    assert "nodes[0]" in fields
    assert "nodes[1].id" in fields
    assert "nodes[3].id" in fields  # duplicate
    assert "nodes[4].type" in fields
    assert any("noname" in w for w in result.warnings)


def test_validate_edge_errors() -> None:
    data = _valid_data(
        nodes=[{"id": "a", "type": "llm", "name": "A"}],
        edges=[
            "not-a-dict",
            {"source": "missing", "target": "a"},
            {"source": "a", "target": "missing"},
        ],
    )
    result = WorkflowIO.validate_workflow(data)
    assert result.success is False
    fields = [e.field for e in result.errors]
    assert "edges[0]" in fields
    assert "edges[1].source" in fields
    assert "edges[2].target" in fields


# ── migrate / import ──────────────────────────────────────────────────────


def test_migrate_same_and_different_version() -> None:
    same, changed = WorkflowIO._migrate({"version": CURRENT_VERSION})
    assert changed is False
    assert same["version"] == CURRENT_VERSION

    migrated, changed = WorkflowIO._migrate({"version": "0.0.1", "metadata": {"name": "old"}})
    assert changed is True
    assert migrated["version"] == CURRENT_VERSION
    assert migrated["metadata"] == {"name": "old"}


def test_import_workflow_success() -> None:
    result = WorkflowIO.import_workflow(_valid_data())
    assert result.success is True
    assert result.workflow is not None
    assert result.workflow.name == "My Flow"
    assert result.workflow_id == result.workflow.id
    assert result.migrated is False
    assert result.original_version == CURRENT_VERSION


def test_import_workflow_migrates_old_version() -> None:
    data = _valid_data(version="0.0.1")
    result = WorkflowIO.import_workflow(data)
    assert result.success is True
    assert result.migrated is True
    assert result.original_version == "0.0.1"


def test_import_workflow_validation_failure_short_circuits() -> None:
    result = WorkflowIO.import_workflow({"nodes": [], "edges": []})
    assert result.success is False
    assert result.workflow is None


def test_import_workflow_deserialize_failure() -> None:
    # config is not a dict -> WorkflowNode validation blows up after validation passes
    data = _valid_data(
        nodes=[{"id": "n1", "type": "llm", "name": "N", "config": ["bad"]}],
        edges=[],
    )
    result = WorkflowIO.import_workflow(data)
    assert result.success is False
    assert result.errors[0].field == "root"
    assert "Failed to construct workflow" in result.errors[0].message


def test_deserialize_workflow_defaults() -> None:
    workflow = _deserialize_workflow(
        {
            "metadata": {},
            "nodes": [{"type": "llm", "name": "N"}],
            "edges": [{}],
        }
    )
    assert workflow.name == "Imported Workflow"
    assert len(workflow.nodes[0].id) == 8  # generated uuid
    assert workflow.edges[0].source == ""
    assert workflow.edges[0].target == ""


def test_validation_error_model() -> None:
    err = WorkflowValidationError(field="f", message="m")
    assert err.field == "f"
    assert err.message == "m"
