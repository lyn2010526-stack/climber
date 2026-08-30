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
from app.workflow.io import WorkflowIO
from app.workflow.registry import NodePort, NodeTypeDefinition, node_registry


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

    def test_edge_preserves_typed_handles(self):
        edge = WorkflowEdge(
            source="node_a",
            target="node_b",
            sourceHandle="result",
            targetHandle="prompt",
        )

        assert edge.source_handle == "result"
        assert edge.target_handle == "prompt"


class TestWorkflow:
    def test_unknown_node_type_is_preserved_for_display(self):
        node = WorkflowNode(type="plugin.missing", name="Missing plugin")

        assert node.type == "plugin.missing"

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
    @pytest.mark.asyncio
    async def test_unknown_node_fails_closed(self):
        from unittest.mock import MagicMock

        workflow = Workflow(
            name="unknown",
            nodes=[WorkflowNode(id="missing", type="plugin.missing", name="Missing plugin")],
        )

        result = await WorkflowEngine(MagicMock(spec=AgentEngine)).execute(workflow)

        assert result.status == "failed"
        assert "Unknown workflow node type" in result.error

    @pytest.mark.asyncio
    async def test_registered_custom_executor_runs(self):
        from unittest.mock import MagicMock

        async def execute(node, inputs, context):
            return {"echo": inputs["value"], "user_id": context["user_id"]}

        node_registry.register(
            NodeTypeDefinition(
                type="custom.echo.test",
                label="Echo",
                inputs=[NodePort(id="value")],
                outputs=[NodePort(id="result")],
            ),
            execute,
        )
        try:
            node = WorkflowNode(id="echo", type="custom.echo.test", name="Echo")
            result = await WorkflowEngine(MagicMock(spec=AgentEngine)).execute_single_node(
                node,
                inputs={"value": "hello"},
                user_id="user-1",
            )
        finally:
            node_registry.unregister("custom.echo.test")

        assert result["status"] == "completed"
        assert result["output"] == {"echo": "hello", "user_id": "user-1"}


class TestWorkflowGraphContract:
    def test_graph_conversion_preserves_unknown_type_and_handles(self):
        from app.core.workflow_executor import build_workflow_from_graph

        workflow = build_workflow_from_graph(
            [
                {"id": "source", "type": "input", "data": {"label": "Input"}},
                {"id": "missing", "type": "plugin.missing", "data": {"label": "Missing"}},
            ],
            [{
                "source": "source",
                "target": "missing",
                "sourceHandle": "value",
                "targetHandle": "input",
            }],
        )

        assert workflow.nodes[1].type == "plugin.missing"
        assert workflow.edges[0].source_handle == "value"
        assert workflow.edges[0].target_handle == "input"

    def test_graph_validation_rejects_incompatible_handles(self):
        from app.core.workflow_executor import validate_workflow_graph

        result = validate_workflow_graph(
            [
                {"id": "llm", "type": "llm", "data": {"model": "test"}},
                {"id": "iterator", "type": "iterator", "data": {}},
            ],
            [{
                "source": "llm",
                "target": "iterator",
                "sourceHandle": "response",
                "targetHandle": "items",
            }],
        )

        assert result["valid"] is False
        assert any("incompatible" in error.lower() for error in result["errors"])

    @pytest.mark.parametrize(
        ("nodes", "edges", "message"),
        [
            ([42], [], "nodes[0] must be an object"),
            ([{"id": "input", "type": "input", "data": {}}], [42], "edges[0] must be an object"),
            ([{"type": "input", "data": {}}], [], "nodes[0].id is required"),
            ([{"id": "input", "type": "input", "data": []}], [], "nodes[0].data must be an object"),
            ([{"id": "input", "type": "input", "data": {}}], [{"source": [], "target": "input"}], "edges[0].source must be a string"),
            ([{"id": "input", "type": "input", "data": {}}], [{"source": "input", "target": "input", "sourceHandle": []}], "edges[0].sourceHandle must be a string"),
        ],
    )
    def test_graph_validation_rejects_malformed_graph_values(self, nodes, edges, message):
        from app.core.workflow_executor import validate_workflow_graph

        with pytest.raises(ValueError, match=message.replace("[", r"\[").replace("]", r"\]")):
            validate_workflow_graph(nodes, edges)

    def test_graph_validation_accepts_null_optional_handles(self):
        from app.core.workflow_executor import validate_workflow_graph

        result = validate_workflow_graph(
            [
                {"id": "input", "type": "input", "data": {}},
                {"id": "output", "type": "output", "data": {}},
            ],
            [{"source": "input", "target": "output", "sourceHandle": None, "targetHandle": None}],
        )

        assert result["valid"] is True

    def test_workflow_io_round_trips_handles_and_unknown_nodes(self):
        workflow = Workflow(
            name="plugins",
            nodes=[WorkflowNode(id="plugin", type="plugin.missing", name="Missing")],
            edges=[WorkflowEdge(
                source="plugin",
                target="plugin",
                source_handle="result",
                target_handle="input",
            )],
        )

        exported = WorkflowIO.export_workflow(workflow)
        imported = WorkflowIO.import_workflow(exported)

        assert exported["edges"][0]["sourceHandle"] == "result"
        assert imported.success is True
        assert imported.workflow is not None
        assert imported.workflow.nodes[0].type == "plugin.missing"
        assert imported.workflow.edges[0].target_handle == "input"


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

    def test_resolve_inputs_routes_typed_edge_handles(self):
        from unittest.mock import MagicMock

        wf_engine = WorkflowEngine(MagicMock(spec=AgentEngine))
        workflow = Workflow(
            name="typed",
            nodes=[
                WorkflowNode(id="source", type=NodeType.LLM, name="source", output={"response": "hello"}),
                WorkflowNode(id="target", type=NodeType.TOOL, name="target"),
            ],
            edges=[WorkflowEdge(
                source="source",
                target="target",
                source_handle="response",
                target_handle="input",
            )],
        )

        assert wf_engine._resolve_inputs(workflow.get_node("target"), workflow) == {"input": "hello"}

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

    @pytest.mark.asyncio
    async def test_tool_node_raises_when_tool_execution_fails(self, monkeypatch):
        from unittest.mock import MagicMock

        from app.core.parallel import ParallelToolExecutor, ToolExecutionResult

        engine = MagicMock(spec=AgentEngine)
        engine.tool_registry = MagicMock()
        wf_engine = WorkflowEngine(engine)
        node = WorkflowNode(
            id="tool",
            type=NodeType.TOOL,
            name="dangerous tool",
            config={"tool_name": "run_command", "tool_inputs": {"command": "ls"}},
        )

        async def fail_execution(self, tool_calls):
            return [ToolExecutionResult(tool_name="run_command", success=False, error="permission denied")]

        monkeypatch.setattr(ParallelToolExecutor, "execute_all", fail_execution)

        with pytest.raises(RuntimeError, match="permission denied"):
            await wf_engine._execute_tool_node(node, {}, workflow_id="wf-1", user_id="user-1")

    @pytest.mark.asyncio
    async def test_tool_node_uses_engine_registry_and_propagates_tool_error(self):
        from unittest.mock import MagicMock

        from app.tools import ToolRegistry

        registry = ToolRegistry()

        @registry.tool(name="explode", description="Always fails")
        async def explode() -> str:
            raise RuntimeError("tool exploded")

        engine = MagicMock(spec=AgentEngine)
        engine.tool_registry = registry
        engine.get_permission_config.return_value = None
        wf_engine = WorkflowEngine(engine)
        node = WorkflowNode(
            id="tool",
            type=NodeType.TOOL,
            name="exploding tool",
            config={"tool_name": "explode", "tool_inputs": {}},
        )

        with pytest.raises(RuntimeError, match="tool exploded"):
            await wf_engine._execute_tool_node(node, {}, workflow_id="workflow-id", user_id="user-1")

    @pytest.mark.asyncio
    async def test_llm_node_uses_connected_prompt_input_when_config_prompt_is_empty(self):
        from unittest.mock import MagicMock

        engine = MagicMock(spec=AgentEngine)
        session = object()
        engine.create_session.return_value = session
        received: list[str] = []

        async def run(_session, prompt):
            received.append(prompt)
            yield type("Event", (), {"type": type("Type", (), {"value": "text"})(), "data": {"content": "ok"}})()

        engine.run = run
        wf_engine = WorkflowEngine(engine)
        node = WorkflowNode(
            id="llm",
            type=NodeType.LLM,
            name="llm",
            config={"model_id": "gpt-4", "prompt": ""},
        )

        result = await wf_engine._execute_llm_node(node, {"prompt": "connected prompt"}, "user-1")

        assert received == ["connected prompt"]
        assert result["response"] == "ok"


@pytest.mark.asyncio
async def test_node_types_and_single_node_api(client):
    response = await client.get("/api/v1/workflows/node-types")

    assert response.status_code == 200
    assert len(response.json()) == 7

    for node_type in ("input", "output"):
        response = await client.post(
            "/api/v1/workflows/nodes/run",
            json={
                "node": {"id": node_type, "type": node_type, "data": {"label": node_type}},
                "inputs": {"value": "hello"},
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    response = await client.post(
        "/api/v1/workflows/nodes/run",
        json={
            "node": {"id": "missing", "type": "plugin.missing", "data": {"label": "Missing"}},
            "inputs": {"value": "hello"},
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert "Unknown workflow node type" in response.json()["error"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "error"),
    [
        ({"node": {"id": "code", "type": "code", "data": []}, "inputs": {}}, "node.data must be an object"),
        ({"node": {"id": "code", "type": "code", "data": {}}, "inputs": []}, "inputs must be an object"),
        (
            {"node": {"id": "iterator", "type": "iterator", "data": {"max_iterations": "many"}}, "inputs": {}},
            "iterator max_iterations must be an integer",
        ),
        (
            {"node": {"id": "iterator", "type": "iterator", "data": {"max_iterations": 0}}, "inputs": {}},
            "iterator max_iterations must be between 1 and 10000",
        ),
    ],
)
async def test_single_node_api_maps_invalid_payloads_to_422(client, payload, error):
    response = await client.post("/api/v1/workflows/nodes/run", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"] == {"errors": [error]}


@pytest.mark.asyncio
async def test_iterator_node_parses_and_limits_max_iterations():
    from unittest.mock import MagicMock

    wf_engine = WorkflowEngine(MagicMock(spec=AgentEngine))
    node = WorkflowNode(
        id="iterator",
        type=NodeType.ITERATOR,
        name="iterator",
        config={
            "collection": "items",
            "item_var": "item",
            "max_iterations": "2",
            "transform": "item",
        },
    )

    result = await wf_engine._execute_iterator_node(
        node,
        {"items": [1, 2, 3]},
        "user-1",
        set(),
    )

    assert result["results"] == [1, 2]


@pytest.mark.asyncio
async def test_workflow_run_rejects_invalid_typed_connection(client):
    response = await client.post(
        "/api/v1/workflows/ad-hoc/run",
        json={
            "nodes": [
                {"id": "input", "type": "input", "data": {}},
                {"id": "llm", "type": "llm", "data": {"model": "test"}},
                {"id": "iterator", "type": "iterator", "data": {}},
                {"id": "output", "type": "output", "data": {}},
            ],
            "edges": [{
                "source": "llm",
                "target": "iterator",
                "sourceHandle": "response",
                "targetHandle": "items",
            }],
        },
    )

    assert response.status_code == 422
    assert any("incompatible" in error.lower() for error in response.json()["detail"]["errors"])


@pytest.mark.asyncio
async def test_workflow_run_maps_malformed_graph_to_422(client):
    response = await client.post(
        "/api/v1/workflows/ad-hoc/run",
        json={"nodes": [42], "edges": []},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {"errors": ["nodes[0] must be an object"]}


@pytest.mark.asyncio
async def test_workflow_run_maps_malformed_edge_fields_to_422(client):
    response = await client.post(
        "/api/v1/workflows/ad-hoc/run",
        json={
            "nodes": [
                {"id": "input", "type": "input", "data": {}},
                {"id": "output", "type": "output", "data": {}},
            ],
            "edges": [{"source": [], "target": "output"}],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {"errors": ["edges[0].source must be a string"]}


class TestWorkflowResilience:
    """Node-level retry and failure strategies (Dify-style)."""

    def _engine(self):
        from unittest.mock import MagicMock

        engine = MagicMock(spec=AgentEngine)
        engine.tool_registry = MagicMock()
        return WorkflowEngine(engine)

    def _make_workflow(self, tool_node, extra_nodes=None, extra_edges=None):
        nodes = [
            WorkflowNode(id="start", type=NodeType.START, name="start"),
            tool_node,
            WorkflowNode(id="end", type=NodeType.END, name="end"),
        ]
        edges = [
            WorkflowEdge(source="start", target=tool_node.id),
            WorkflowEdge(source=tool_node.id, target="end"),
        ]
        if extra_nodes:
            nodes.extend(extra_nodes)
        if extra_edges:
            edges.extend(extra_edges)
        return Workflow(name="resilience", nodes=nodes, edges=edges)

    @pytest.mark.asyncio
    async def test_retry_recovers_transient_failure(self, monkeypatch):
        """Transient failure retried per node config; workflow completes."""
        from app.core.parallel import ParallelToolExecutor, ToolExecutionResult

        attempts = {"n": 0}

        async def flaky(self, tool_calls):
            attempts["n"] += 1
            if attempts["n"] < 3:
                return [ToolExecutionResult(tool_name="flaky", success=False, error="connection timeout")]
            return [ToolExecutionResult(tool_name="flaky", success=True, result="ok")]

        monkeypatch.setattr(ParallelToolExecutor, "execute_all", flaky)

        tool_node = WorkflowNode(
            id="t1",
            type=NodeType.TOOL,
            name="flaky tool",
            config={
                "tool_name": "flaky",
                "tool_inputs": {},
                "retry": {"max_retries": 3, "base_delay": 0, "max_delay": 0},
            },
        )
        wf = self._make_workflow(tool_node)
        result = await self._engine().execute(wf, user_inputs={"q": "x"})

        assert result.status == "completed"
        assert attempts["n"] == 3
        assert wf.get_node("t1").status == NodeStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_retry_exhausted_fails_workflow(self, monkeypatch):
        """Retries exhausted with default strategy -> workflow still fails (backward compat)."""
        from app.core.parallel import ParallelToolExecutor, ToolExecutionResult

        attempts = {"n": 0}

        async def always_fail(self, tool_calls):
            attempts["n"] += 1
            return [ToolExecutionResult(tool_name="bad", success=False, error="503 unavailable")]

        monkeypatch.setattr(ParallelToolExecutor, "execute_all", always_fail)

        tool_node = WorkflowNode(
            id="t1",
            type=NodeType.TOOL,
            name="bad tool",
            config={
                "tool_name": "bad",
                "tool_inputs": {},
                "retry": {"max_retries": 2, "base_delay": 0, "max_delay": 0},
            },
        )
        wf = self._make_workflow(tool_node)
        result = await self._engine().execute(wf)

        assert result.status == "failed"
        assert attempts["n"] == 3  # initial + 2 retries

    @pytest.mark.asyncio
    async def test_permanent_error_not_retried(self, monkeypatch):
        """Permanent errors (invalid input) skip retries entirely."""
        from app.core.parallel import ParallelToolExecutor

        attempts = {"n": 0}

        async def perm_fail(self, tool_calls):
            attempts["n"] += 1
            raise ValueError("invalid input schema")

        monkeypatch.setattr(ParallelToolExecutor, "execute_all", perm_fail)

        tool_node = WorkflowNode(
            id="t1",
            type=NodeType.TOOL,
            name="perm tool",
            config={
                "tool_name": "bad",
                "tool_inputs": {},
                "retry": {"max_retries": 3, "base_delay": 0, "max_delay": 0},
            },
        )
        wf = self._make_workflow(tool_node)
        result = await self._engine().execute(wf)

        assert result.status == "failed"
        assert attempts["n"] == 1

    @pytest.mark.asyncio
    async def test_on_failure_default_value_continues(self, monkeypatch):
        """on_failure=default_value degrades gracefully and workflow completes."""
        from app.core.parallel import ParallelToolExecutor, ToolExecutionResult

        async def fail(self, tool_calls):
            return [ToolExecutionResult(tool_name="bad", success=False, error="boom")]

        monkeypatch.setattr(ParallelToolExecutor, "execute_all", fail)

        tool_node = WorkflowNode(
            id="t1",
            type=NodeType.TOOL,
            name="degradable tool",
            config={
                "tool_name": "bad",
                "tool_inputs": {},
                "on_failure": "default_value",
                "default_value": {"result": "fallback"},
            },
        )
        wf = self._make_workflow(tool_node)
        result = await self._engine().execute(wf)

        assert result.status == "completed"
        node = wf.get_node("t1")
        assert node.status == NodeStatus.COMPLETED
        assert node.output == {"result": "fallback"}
        assert "boom" in node.error

    @pytest.mark.asyncio
    async def test_on_failure_fail_branch_routes(self, monkeypatch):
        """on_failure=fail_branch skips success path, executes fail edge branch."""
        from app.core.parallel import ParallelToolExecutor, ToolExecutionResult

        async def fail(self, tool_calls):
            return [ToolExecutionResult(tool_name="bad", success=False, error="boom")]

        monkeypatch.setattr(ParallelToolExecutor, "execute_all", fail)

        tool_node = WorkflowNode(
            id="t1",
            type=NodeType.TOOL,
            name="branchy tool",
            config={
                "tool_name": "bad",
                "tool_inputs": {},
                "on_failure": "fail_branch",
            },
        )
        success_end = WorkflowNode(id="ok_end", type=NodeType.END, name="ok end")
        fail_end = WorkflowNode(id="fail_end", type=NodeType.END, name="fail end")
        wf = Workflow(
            name="branchy",
            nodes=[
                WorkflowNode(id="start", type=NodeType.START, name="start"),
                tool_node,
                success_end,
                fail_end,
            ],
            edges=[
                WorkflowEdge(source="start", target="t1"),
                WorkflowEdge(source="t1", target="ok_end"),
                WorkflowEdge(source="t1", target="fail_end", condition="fail"),
            ],
        )
        result = await self._engine().execute(wf)

        assert result.status == "completed"
        assert wf.get_node("ok_end").status == NodeStatus.PENDING  # never ran
        assert wf.get_node("fail_end").status == NodeStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_fail_branch_without_fail_edge_fails(self, monkeypatch):
        """fail_branch declared but no fail edge -> workflow fails."""
        from app.core.parallel import ParallelToolExecutor, ToolExecutionResult

        async def fail(self, tool_calls):
            return [ToolExecutionResult(tool_name="bad", success=False, error="boom")]

        monkeypatch.setattr(ParallelToolExecutor, "execute_all", fail)

        tool_node = WorkflowNode(
            id="t1",
            type=NodeType.TOOL,
            name="orphan tool",
            config={"tool_name": "bad", "tool_inputs": {}, "on_failure": "fail_branch"},
        )
        wf = self._make_workflow(tool_node)
        result = await self._engine().execute(wf)

        assert result.status == "failed"
