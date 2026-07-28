"""Tests for workflow DAG engine."""

from __future__ import annotations

import pytest

from app.core.agent_engine import AgentEngine
from app.workflow import (
    NodeStatus,
    NodeType,
    Workflow,
    WorkflowEdge,
    WorkflowNode,
)
from app.workflow.engine import WorkflowEngine


class TestWorkflowNode:
    def test_create_node(self):
        node = WorkflowNode(
            type=NodeType.LLM,
            name="generate_text",
            config={"model_id": "gpt-4", "prompt": "Hello {{name}}"},
        )
        assert node.type == NodeType.LLM
        assert node.status == NodeStatus.PENDING
        assert node.id is not None

    def test_create_all_node_types(self):
        for nt in NodeType:
            node = WorkflowNode(type=nt, name=f"test_{nt.value}")
            assert node.type == nt


class TestWorkflowEdge:
    def test_create_edge(self):
        edge = WorkflowEdge(source="node_a", target="node_b")
        assert edge.source == "node_a"
        assert edge.target == "node_b"
        assert edge.condition == ""

    def test_conditional_edge(self):
        edge = WorkflowEdge(source="node_a", target="node_b", condition="result == true")
        assert edge.condition == "result == true"


class TestWorkflow:
    def test_topological_sort_linear(self):
        w = Workflow(name="linear")
        w.nodes = [
            WorkflowNode(id="a", type=NodeType.START, name="start"),
            WorkflowNode(id="b", type=NodeType.LLM, name="llm"),
            WorkflowNode(id="c", type=NodeType.END, name="end"),
        ]
        w.edges = [
            WorkflowEdge(source="a", target="b"),
            WorkflowEdge(source="b", target="c"),
        ]
        layers = w.topological_sort()
        assert len(layers) == 3
        assert layers[0] == ["a"]
        assert layers[1] == ["b"]
        assert layers[2] == ["c"]

    def test_topological_sort_parallel(self):
        w = Workflow(name="parallel")
        w.nodes = [
            WorkflowNode(id="a", type=NodeType.START, name="start"),
            WorkflowNode(id="b", type=NodeType.LLM, name="llm1"),
            WorkflowNode(id="c", type=NodeType.LLM, name="llm2"),
            WorkflowNode(id="d", type=NodeType.END, name="end"),
        ]
        w.edges = [
            WorkflowEdge(source="a", target="b"),
            WorkflowEdge(source="a", target="c"),
            WorkflowEdge(source="b", target="d"),
            WorkflowEdge(source="c", target="d"),
        ]
        layers = w.topological_sort()
        assert len(layers) == 3
        assert layers[0] == ["a"]
        assert set(layers[1]) == {"b", "c"}
        assert layers[2] == ["d"]

    def test_topological_sort_diamond(self):
        w = Workflow(name="diamond")
        w.nodes = [
            WorkflowNode(id="a", type=NodeType.START, name="start"),
            WorkflowNode(id="b", type=NodeType.LLM, name="step1"),
            WorkflowNode(id="c", type=NodeType.LLM, name="step2"),
            WorkflowNode(id="d", type=NodeType.LLM, name="merge"),
            WorkflowNode(id="e", type=NodeType.END, name="end"),
        ]
        w.edges = [
            WorkflowEdge(source="a", target="b"),
            WorkflowEdge(source="a", target="c"),
            WorkflowEdge(source="b", target="d"),
            WorkflowEdge(source="c", target="d"),
            WorkflowEdge(source="d", target="e"),
        ]
        layers = w.topological_sort()
        assert len(layers) == 4
        assert layers[0] == ["a"]
        assert set(layers[1]) == {"b", "c"}
        assert layers[2] == ["d"]
        assert layers[3] == ["e"]

    def test_topological_sort_cycle_detection(self):
        w = Workflow(name="cyclic")
        w.nodes = [
            WorkflowNode(id="a", type=NodeType.START, name="start"),
            WorkflowNode(id="b", type=NodeType.LLM, name="llm"),
        ]
        w.edges = [
            WorkflowEdge(source="a", target="b"),
            WorkflowEdge(source="b", target="a"),
        ]
        with pytest.raises(ValueError, match="Cycle"):
            w.topological_sort()

    def test_get_node(self):
        w = Workflow(name="test")
        node = WorkflowNode(id="n1", type=NodeType.LLM, name="test")
        w.nodes = [node]
        assert w.get_node("n1") == node
        assert w.get_node("nonexistent") is None

    def test_get_predecessors(self):
        w = Workflow(name="test")
        w.nodes = [
            WorkflowNode(id="a", type=NodeType.START, name="start"),
            WorkflowNode(id="b", type=NodeType.LLM, name="llm"),
            WorkflowNode(id="c", type=NodeType.LLM, name="llm2"),
        ]
        w.edges = [
            WorkflowEdge(source="a", target="b"),
            WorkflowEdge(source="a", target="c"),
        ]
        assert set(w.get_predecessors("b")) == {"a"}
        assert set(w.get_predecessors("c")) == {"a"}

    def test_get_successors(self):
        w = Workflow(name="test")
        w.nodes = [
            WorkflowNode(id="a", type=NodeType.START, name="start"),
            WorkflowNode(id="b", type=NodeType.LLM, name="llm"),
        ]
        w.edges = [WorkflowEdge(source="a", target="b")]
        succs = w.get_successors("a")
        assert len(succs) == 1
        assert succs[0].target == "b"


class TestWorkflowEngine:
    def test_resolve_inputs(self):
        from unittest.mock import MagicMock

        engine = MagicMock(spec=AgentEngine)
        wf_engine = WorkflowEngine(engine)

        w = Workflow(name="test")
        w.nodes = [
            WorkflowNode(id="a", type=NodeType.START, name="start", output={"name": "World"}),
            WorkflowNode(id="b", type=NodeType.LLM, name="llm"),
        ]
        w.edges = [WorkflowEdge(source="a", target="b")]

        resolved = wf_engine._resolve_inputs(w.get_node("b"), w)
        assert resolved["name"] == "World"

    def test_resolve_inputs_with_path(self):
        from unittest.mock import MagicMock

        engine = MagicMock(spec=AgentEngine)
        wf_engine = WorkflowEngine(engine)

        w = Workflow(name="test")
        w.nodes = [
            WorkflowNode(id="a", type=NodeType.START, name="start", output={"text": "Hello World"}),
            WorkflowNode(
                id="b",
                type=NodeType.LLM,
                name="llm",
                inputs={"message": "a.text"},
            ),
        ]
        w.edges = [WorkflowEdge(source="a", target="b")]

        resolved = wf_engine._resolve_inputs(w.get_node("b"), w)
        assert resolved["message"] == "Hello World"

    def test_render_template(self):
        from unittest.mock import MagicMock

        engine = MagicMock(spec=AgentEngine)
        wf_engine = WorkflowEngine(engine)

        result = wf_engine._render_template("Hello {{name}}, welcome to {{place}}", {"name": "Alice", "place": "NYC"})
        assert result == "Hello Alice, welcome to NYC"

    def test_render_template_missing_vars(self):
        from unittest.mock import MagicMock

        engine = MagicMock(spec=AgentEngine)
        wf_engine = WorkflowEngine(engine)

        result = wf_engine._render_template("Hello {{name}}", {})
        assert result == "Hello {{name}}"

    def test_condition_node_equals(self):
        from unittest.mock import MagicMock

        engine = MagicMock(spec=AgentEngine)
        wf_engine = WorkflowEngine(engine)

        result = wf_engine._execute_condition_node(
            WorkflowNode(
                id="cond",
                type=NodeType.CONDITION,
                name="check",
                config={"field": "status", "operator": "equals", "value": "success"},
            ),
            {"status": "success"},
        )
        assert result["condition_result"] is True

    def test_condition_node_not_equals(self):
        from unittest.mock import MagicMock

        engine = MagicMock(spec=AgentEngine)
        wf_engine = WorkflowEngine(engine)

        result = wf_engine._execute_condition_node(
            WorkflowNode(
                id="cond",
                type=NodeType.CONDITION,
                name="check",
                config={"field": "status", "operator": "equals", "value": "success"},
            ),
            {"status": "failed"},
        )
        assert result["condition_result"] is False

    def test_condition_node_contains(self):
        from unittest.mock import MagicMock

        engine = MagicMock(spec=AgentEngine)
        wf_engine = WorkflowEngine(engine)

        result = wf_engine._execute_condition_node(
            WorkflowNode(
                id="cond",
                type=NodeType.CONDITION,
                name="check",
                config={"field": "text", "operator": "contains", "value": "error"},
            ),
            {"text": "an error occurred"},
        )
        assert result["condition_result"] is True

    def test_condition_node_not_empty(self):
        from unittest.mock import MagicMock

        engine = MagicMock(spec=AgentEngine)
        wf_engine = WorkflowEngine(engine)

        result = wf_engine._execute_condition_node(
            WorkflowNode(
                id="cond",
                type=NodeType.CONDITION,
                name="check",
                config={"field": "value", "operator": "not_empty"},
            ),
            {"value": "something"},
        )
        assert result["condition_result"] is True

    def test_code_node(self):
        from unittest.mock import MagicMock

        engine = MagicMock(spec=AgentEngine)
        wf_engine = WorkflowEngine(engine)

        result = wf_engine._execute_code_node(
            WorkflowNode(
                id="code",
                type=NodeType.CODE,
                name="process",
                config={"code": "result = inputs['x'] + inputs['y']"},
            ),
            {"x": 10, "y": 20},
        )
        assert result["result"] == 30

    def test_execute_simple_workflow(self):
        """Test executing a simple start -> end workflow."""
        from unittest.mock import MagicMock

        engine = MagicMock(spec=AgentEngine)
        wf_engine = WorkflowEngine(engine)

        w = Workflow(name="simple")
        w.nodes = [
            WorkflowNode(id="start", type=NodeType.START, name="start"),
            WorkflowNode(id="end", type=NodeType.END, name="end"),
        ]
        w.edges = [WorkflowEdge(source="start", target="end")]

        import asyncio
        result = asyncio.run(wf_engine.execute(w, user_inputs={"query": "hello"}))
        assert result.status == "completed"
