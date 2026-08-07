"""Tests for WorkflowIO import/export."""

from __future__ import annotations

import json

from app.workflow import Workflow, WorkflowEdge, WorkflowNode
from app.workflow.io import (
    CURRENT_VERSION,
    WorkflowIO,
    _deserialize_workflow,
    _serialize_workflow,
)


def make_test_workflow():
    """Create a simple test workflow."""
    return Workflow(
        id="test-wf-1",
        name="Test Workflow",
        description="A test workflow",
        nodes=[
            WorkflowNode(id="start", type="start", name="Start"),
            WorkflowNode(id="llm", type="llm", name="LLM", config={"provider": "openai"}),
            WorkflowNode(id="end", type="end", name="End"),
        ],
        edges=[
            WorkflowEdge(source="start", target="llm"),
            WorkflowEdge(source="llm", target="end"),
        ],
    )


class TestSerializeWorkflow:
    """Tests for _serialize_workflow."""

    def test_serializes_basic_fields(self):
        wf = make_test_workflow()
        result = _serialize_workflow(wf)
        assert result["id"] == "test-wf-1"
        assert result["name"] == "Test Workflow"
        assert result["description"] == "A test workflow"

    def test_serializes_nodes(self):
        wf = make_test_workflow()
        result = _serialize_workflow(wf)
        assert len(result["nodes"]) == 3
        assert result["nodes"][0]["id"] == "start"
        assert result["nodes"][0]["type"] == "start"

    def test_serializes_edges(self):
        wf = make_test_workflow()
        result = _serialize_workflow(wf)
        assert len(result["edges"]) == 2
        assert result["edges"][0]["source"] == "start"
        assert result["edges"][0]["target"] == "llm"


class TestDeserializeWorkflow:
    """Tests for _deserialize_workflow."""

    def test_deserializes_basic_fields(self):
        data = {
            "id": "wf-1",
            "metadata": {"name": "Test", "description": "Desc"},
            "nodes": [{"id": "n1", "type": "start", "name": "Start"}],
            "edges": [],
        }
        wf = _deserialize_workflow(data)
        assert wf.id == "wf-1"
        assert wf.name == "Test"

    def test_generates_id_if_missing(self):
        data = {
            "metadata": {"name": "Test"},
            "nodes": [{"id": "n1", "type": "start", "name": "Start"}],
            "edges": [],
        }
        wf = _deserialize_workflow(data)
        assert wf.id is not None

    def test_handles_empty_nodes(self):
        data = {
            "metadata": {"name": "Empty"},
            "nodes": [],
            "edges": [],
        }
        wf = _deserialize_workflow(data)
        assert len(wf.nodes) == 0


class TestExportWorkflow:
    """Tests for WorkflowIO.export_workflow."""

    def test_export_includes_version(self):
        wf = make_test_workflow()
        result = WorkflowIO.export_workflow(wf)
        assert result["version"] == CURRENT_VERSION

    def test_export_includes_metadata(self):
        wf = make_test_workflow()
        result = WorkflowIO.export_workflow(wf)
        assert result["metadata"]["name"] == "Test Workflow"
        assert result["metadata"]["description"] == "A test workflow"

    def test_export_includes_nodes_and_edges(self):
        wf = make_test_workflow()
        result = WorkflowIO.export_workflow(wf)
        assert len(result["nodes"]) == 3
        assert len(result["edges"]) == 2

    def test_export_includes_timestamp(self):
        wf = make_test_workflow()
        result = WorkflowIO.export_workflow(wf)
        assert "exported_at" in result


class TestExportToFile:
    """Tests for WorkflowIO.export_to_file."""

    def test_export_json(self, tmp_path):
        wf = make_test_workflow()
        path = tmp_path / "workflow.json"
        result = WorkflowIO.export_to_file(wf, path)
        assert result.exists()
        assert result.suffix == ".json"

    def test_export_json_content(self, tmp_path):
        wf = make_test_workflow()
        path = tmp_path / "workflow.json"
        WorkflowIO.export_to_file(wf, path)
        data = json.loads(path.read_text())
        assert data["metadata"]["name"] == "Test Workflow"

    def test_export_yaml(self, tmp_path):
        wf = make_test_workflow()
        path = tmp_path / "workflow.yaml"
        try:
            result = WorkflowIO.export_to_file(wf, path, fmt="yaml")
            assert result.exists()
        except RuntimeError as e:
            assert "PyYAML" in str(e)


class TestValidateWorkflow:
    """Tests for WorkflowIO.validate_workflow."""

    def test_valid_workflow(self):
        data = {
            "version": "1.0.0",
            "metadata": {"name": "Test"},
            "nodes": [{"id": "n1", "type": "start", "name": "Start"}],
            "edges": [],
        }
        result = WorkflowIO.validate_workflow(data)
        assert result.success is True

    def test_not_dict(self):
        result = WorkflowIO.validate_workflow("not a dict")
        assert result.success is False

    def test_missing_version(self):
        data = {
            "metadata": {},
            "nodes": [{"id": "n1", "type": "start", "name": "Start"}],
            "edges": [],
        }
        result = WorkflowIO.validate_workflow(data)
        assert result.success is False
        assert any(e.field == "version" for e in result.errors)

    def test_empty_nodes(self):
        data = {
            "version": "1.0.0",
            "metadata": {},
            "nodes": [],
            "edges": [],
        }
        result = WorkflowIO.validate_workflow(data)
        assert result.success is False

    def test_duplicate_node_ids(self):
        data = {
            "version": "1.0.0",
            "metadata": {},
            "nodes": [
                {"id": "n1", "type": "start", "name": "A"},
                {"id": "n1", "type": "end", "name": "B"},
            ],
            "edges": [],
        }
        result = WorkflowIO.validate_workflow(data)
        assert result.success is False
        assert any("Duplicate" in e.message for e in result.errors)

    def test_unknown_node_type(self):
        data = {
            "version": "1.0.0",
            "metadata": {},
            "nodes": [{"id": "n1", "type": "unknown_type", "name": "X"}],
            "edges": [],
        }
        result = WorkflowIO.validate_workflow(data)
        assert result.success is False
        assert any("Unknown node type" in e.message for e in result.errors)

    def test_edge_unknown_source(self):
        data = {
            "version": "1.0.0",
            "metadata": {},
            "nodes": [{"id": "n1", "type": "start", "name": "Start"}],
            "edges": [{"source": "nonexistent", "target": "n1"}],
        }
        result = WorkflowIO.validate_workflow(data)
        assert result.success is False
        assert any("unknown source" in e.message for e in result.errors)

    def test_edge_unknown_target(self):
        data = {
            "version": "1.0.0",
            "metadata": {},
            "nodes": [{"id": "n1", "type": "start", "name": "Start"}],
            "edges": [{"source": "n1", "target": "nonexistent"}],
        }
        result = WorkflowIO.validate_workflow(data)
        assert result.success is False
        assert any("unknown target" in e.message for e in result.errors)

    def test_node_missing_name_warning(self):
        data = {
            "version": "1.0.0",
            "metadata": {},
            "nodes": [{"id": "n1", "type": "start", "name": ""}],
            "edges": [],
        }
        result = WorkflowIO.validate_workflow(data)
        assert result.success is True
        assert len(result.warnings) > 0


class TestMigrate:
    """Tests for WorkflowIO._migrate."""

    def test_same_version_no_migration(self):
        data = {"version": "1.0.0", "metadata": {}, "nodes": [], "edges": []}
        result, migrated = WorkflowIO._migrate(data)
        assert migrated is False
        assert result == data

    def test_old_version_migrated(self):
        data = {"version": "0.9.0", "metadata": {}, "nodes": [], "edges": []}
        result, migrated = WorkflowIO._migrate(data)
        assert migrated is True
        assert result["version"] == CURRENT_VERSION


class TestImportWorkflow:
    """Tests for WorkflowIO.import_workflow."""

    def test_import_valid_workflow(self):
        data = {
            "version": "1.0.0",
            "metadata": {"name": "Imported", "description": "Test"},
            "nodes": [{"id": "n1", "type": "start", "name": "Start"}],
            "edges": [],
        }
        result = WorkflowIO.import_workflow(data)
        assert result.success is True
        assert result.workflow is not None

    def test_import_invalid_workflow(self):
        data = {"version": "1.0.0", "metadata": {}, "nodes": []}
        result = WorkflowIO.import_workflow(data)
        assert result.success is False

    def test_import_migrated_workflow(self):
        data = {
            "version": "0.9.0",
            "metadata": {"name": "Old"},
            "nodes": [{"id": "n1", "type": "start", "name": "Start"}],
            "edges": [],
        }
        result = WorkflowIO.import_workflow(data)
        assert result.success is True
        assert result.migrated is True
