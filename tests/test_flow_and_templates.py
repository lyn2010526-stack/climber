"""Tests for the Flow system and workflow templates."""

import pytest
from unittest.mock import MagicMock

from app.core.agent_engine import AgentEngine
from app.multi_agent.flow import (
    FlowExecutor,
    FlowState,
    FlowStatus,
    listen,
    listen_or,
    listen_route,
    router,
    start,
)
from app.workflow import NodeType, Workflow, WorkflowNode, WorkflowEdge
from app.workflow.engine import WorkflowEngine
from app.workflow.templates import WorkflowTemplates


# ── Flow system tests ──


class SampleFlow:
    """A simple flow for testing."""

    def __init__(self):
        self.collected = []

    @start()
    def entry(self, state: FlowState) -> str:
        state.results["entry"] = "started"
        return "started"

    @listen("entry")
    def process(self, state: FlowState) -> str:
        self.collected.append("processed")
        return "processed"

    @listen("entry")
    def alternative(self, state: FlowState) -> str:
        self.collected.append("alternative")
        return "alternative"

    @listen("process", "alternative")
    def combine(self, state: FlowState) -> str:
        self.collected.append("combined")
        return "combined"


class AsyncFlow:
    """Flow with async methods."""

    @start()
    async def fetch(self, state: FlowState) -> str:
        return "fetched_result"

    @listen("fetch")
    async def transform(self, state: FlowState) -> str:
        prev = state.results.get("fetch", "")
        return prev.upper()


class RouterFlow:
    """Flow with routing."""

    @start()
    def entry(self, state: FlowState) -> str:
        return "data"

    @router("entry")
    def route(self, state: FlowState) -> str:
        result = state.results.get("entry", "")
        if result == "data":
            return "path_a"
        return "path_b"

    @listen_route(route, "path_a")
    def handle_a(self, state: FlowState) -> str:
        return "handled_a"

    @listen_route(route, "path_b")
    def handle_b(self, state: FlowState) -> str:
        return "handled_b"


class OrTriggerFlow:
    """Flow with OR trigger."""

    @start()
    def task_a(self, state: FlowState) -> str:
        return "a_done"

    @start()
    def task_b(self, state: FlowState) -> str:
        return "b_done"

    @listen_or("task_a", "task_b")
    def early_response(self, state: FlowState) -> str:
        return "early"


class ErrorFlow:
    """Flow that raises errors."""

    @start()
    def bad_step(self, state: FlowState) -> str:
        raise ValueError("intentional error")

    @listen("bad_step")
    def never_runs(self, state: FlowState) -> str:
        return "should_not_reach"


@pytest.fixture
def flow_executor():
    agent_engine = MagicMock(spec=AgentEngine)
    model_registry = MagicMock()
    tool_registry = MagicMock()
    return FlowExecutor(agent_engine, model_registry, tool_registry)


class TestFlowDecorators:
    """Test decorator markers."""

    def test_start_marker(self):
        @start()
        def my_method(self, state):
            pass

        assert hasattr(my_method, '_flow_start')
        assert my_method._flow_start is True

    def test_listen_marker(self):
        @listen("method_a", "method_b")
        def my_method(self, state):
            pass

        assert hasattr(my_method, '_flow_listens')
        assert my_method._flow_listens == ["method_a", "method_b"]
        assert my_method._flow_trigger == "all"

    def test_listen_or_marker(self):
        @listen_or("method_a", "method_b")
        def my_method(self, state):
            pass

        assert my_method._flow_trigger == "any"

    def test_router_marker(self):
        @router("method_a")
        def my_method(self, state):
            pass

        assert hasattr(my_method, '_flow_returns_routes')
        assert my_method._flow_returns_routes is True

    def test_listen_route_marker(self):
        def dummy_router(self, state):
            pass

        @listen_route(dummy_router, "label_a")
        def my_method(self, state):
            pass

        assert my_method._flow_listens == ["dummy_router"]
        assert my_method._flow_route_label == "label_a"
        assert my_method._flow_trigger == "route"

    def test_listen_with_callable(self):
        def dummy(self, state):
            pass

        @listen(dummy)
        def my_method(self, state):
            pass

        assert my_method._flow_listens == ["dummy"]


class TestFlowState:
    """Test FlowState model."""

    def test_default_creation(self):
        state = FlowState()
        assert state.flow_id is not None
        assert len(state.flow_id) == 8
        assert state.results == {}
        assert state.errors == {}

    def test_with_initial_data(self):
        state = FlowState()
        state.results["key"] = "value"
        assert state.results["key"] == "value"

    def test_error_tracking(self):
        state = FlowState()
        state.errors["bad"] = "failed"
        assert state.errors["bad"] == "failed"


class TestFlowExecution:
    """Test FlowExecutor.execute()."""

    @pytest.mark.asyncio
    async def test_simple_flow(self, flow_executor):
        flow = SampleFlow()
        state = await flow_executor.execute(flow)
        assert "entry" in state.results
        assert state.results["entry"] == "started"
        assert "process" in state.results
        assert "alternative" in state.results
        assert "combine" in state.results
        assert len(state.errors) == 0

    @pytest.mark.asyncio
    async def test_async_flow(self, flow_executor):
        flow = AsyncFlow()
        state = await flow_executor.execute(flow)
        assert state.results["fetch"] == "fetched_result"
        assert state.results["transform"] == "FETCHED_RESULT"

    @pytest.mark.asyncio
    async def test_router_flow_path_a(self, flow_executor):
        flow = RouterFlow()
        state = await flow_executor.execute(flow)
        assert "handle_a" in state.results
        assert state.results["handle_a"] == "handled_a"
        assert "handle_b" not in state.results

    @pytest.mark.asyncio
    async def test_or_trigger_flow(self, flow_executor):
        flow = OrTriggerFlow()
        state = await flow_executor.execute(flow)
        assert "task_a" in state.results
        assert "task_b" in state.results
        assert "early_response" in state.results

    @pytest.mark.asyncio
    async def test_error_flow(self, flow_executor):
        flow = ErrorFlow()
        state = await flow_executor.execute(flow)
        assert "bad_step" in state.errors
        assert "intentional error" in state.errors["bad_step"]

    @pytest.mark.asyncio
    async def test_initial_state(self, flow_executor):
        flow = SampleFlow()
        state = await flow_executor.execute(flow, initial_state={"metadata": {"user": "test"}})
        assert state.metadata["user"] == "test"


# ── Workflow template tests ──


class TestWorkflowTemplates:
    """Test pre-built workflow templates."""

    def test_simple_qa(self):
        wf = WorkflowTemplates.simple_qa(
            provider="openai",
            model_id="gpt-4",
            api_key="sk-test",
        )
        assert wf.name == "Simple QA"
        assert len(wf.nodes) == 3
        assert len(wf.edges) == 2
        assert wf.nodes[0].type == NodeType.START
        assert wf.nodes[1].type == NodeType.LLM
        assert wf.nodes[2].type == NodeType.END

    def test_tool_use(self):
        wf = WorkflowTemplates.tool_use(
            tool_name="search",
            provider="openai",
            model_id="gpt-4",
            api_key="sk-test",
        )
        assert wf.name == "Tool Use"
        node_types = [n.type for n in wf.nodes]
        assert NodeType.START in node_types
        assert NodeType.LLM in node_types
        assert NodeType.CONDITION in node_types
        assert NodeType.TOOL in node_types

    def test_chain_of_thought(self):
        wf = WorkflowTemplates.chain_of_thought(
            provider="openai",
            model_id="gpt-4",
            api_key="sk-test",
            steps=3,
        )
        assert wf.name == "Chain of Thought"
        llm_nodes = [n for n in wf.nodes if n.type == NodeType.LLM]
        assert len(llm_nodes) == 3

    def test_map_reduce(self):
        wf = WorkflowTemplates.map_reduce(
            provider="openai",
            model_id="gpt-4",
            api_key="sk-test",
        )
        assert wf.name == "Map Reduce"
        iterator_nodes = [n for n in wf.nodes if n.type == NodeType.ITERATOR]
        assert len(iterator_nodes) == 1

    def test_conditional_branch(self):
        wf = WorkflowTemplates.conditional_branch(
            provider="openai",
            model_id="gpt-4",
            api_key="sk-test",
            condition_var="start.input",
            condition_value="yes",
            true_prompt="Affirmative",
            false_prompt="Negative",
        )
        assert wf.name == "Conditional Branch"
        cond_nodes = [n for n in wf.nodes if n.type == NodeType.CONDITION]
        assert len(cond_nodes) == 1
        llm_nodes = [n for n in wf.nodes if n.type == NodeType.LLM]
        assert len(llm_nodes) == 2

    def test_list_templates(self):
        templates = WorkflowTemplates.list_templates()
        assert len(templates) >= 5
        ids = [t["id"] for t in templates]
        assert "simple_qa" in ids
        assert "tool_use" in ids
        assert "chain_of_thought" in ids
        assert "map_reduce" in ids
        assert "conditional_branch" in ids

    def test_templates_are_valid_dags(self):
        """All templates must form valid DAGs."""
        configs = [
            ("simple_qa", {}),
            ("tool_use", {"tool_name": "search"}),
            ("chain_of_thought", {"steps": 2}),
            ("map_reduce", {}),
            ("conditional_branch", {
                "condition_var": "start.input",
                "condition_value": "yes",
                "true_prompt": "Yes",
                "false_prompt": "No",
            }),
        ]
        for template_id, extra in configs:
            wf = getattr(WorkflowTemplates, template_id)(
                provider="openai",
                model_id="gpt-4",
                api_key="sk-test",
                **extra,
            )
            # Should not raise
            layers = wf.topological_sort()
            assert len(layers) > 0
            # All nodes should be reachable
            all_node_ids = {n.id for n in wf.nodes}
            layered_ids = set()
            for layer in layers:
                layered_ids.update(layer)
            assert all_node_ids == layered_ids


# ── Workflow engine conditional branching tests ──


class TestWorkflowConditionBranching:
    """Test conditional branching with skip logic."""

    def test_condition_with_workflow_context(self):
        engine = MagicMock(spec=AgentEngine)
        wf_engine = WorkflowEngine(engine)

        # Test with workflow=None (backward compat)
        result = wf_engine._execute_condition_node(
            WorkflowNode(
                id="cond",
                type=NodeType.CONDITION,
                name="check",
                config={"field": "status", "operator": "equals", "value": "ok"},
            ),
            {"status": "ok"},
        )
        assert isinstance(result, dict)
        assert result["condition_result"] is True

    def test_condition_node_with_workflow_skips_branches(self):
        """When condition is false, true branch should be skipped."""
        engine = MagicMock(spec=AgentEngine)
        wf_engine = WorkflowEngine(engine)

        wf = Workflow(name="branch-test")
        wf.nodes = [
            WorkflowNode(id="start", type=NodeType.START, name="start"),
            WorkflowNode(
                id="cond",
                type=NodeType.CONDITION,
                name="check",
                config={"variable": "status", "operator": "equals", "value": "ok"},
            ),
            WorkflowNode(id="true_path", type=NodeType.LLM, name="true"),
            WorkflowNode(id="false_path", type=NodeType.LLM, name="false"),
            WorkflowNode(id="end", type=NodeType.END, name="end"),
        ]
        wf.edges = [
            WorkflowEdge(source="start", target="cond"),
            WorkflowEdge(source="cond", target="true_path", condition="true"),
            WorkflowEdge(source="cond", target="false_path", condition="false"),
            WorkflowEdge(source="true_path", target="end"),
            WorkflowEdge(source="false_path", target="end"),
        ]

        # When status != ok, true_path should be skipped
        output, skip_targets = wf_engine._execute_condition_node(
            wf.get_node("cond"),
            {"status": "error"},
            wf,
        )
        assert output["condition_result"] is False
        assert "true_path" in skip_targets
        assert "false_path" not in skip_targets


class TestWorkflowIterator:
    """Test iterator node execution."""

    @pytest.mark.asyncio
    async def test_iterator_basic(self):
        engine = MagicMock(spec=AgentEngine)
        wf_engine = WorkflowEngine(engine)

        result = await wf_engine._execute_iterator_node(
            WorkflowNode(
                id="iter",
                type=NodeType.ITERATOR,
                name="loop",
                config={
                    "collection": "items",
                    "item_var": "x",
                    "transform": "x * 2",
                    "max_iterations": 10,
                },
            ),
            {"items": [1, 2, 3]},
            "user-1",
            set(),
        )
        assert result["results"] == [2, 4, 6]
        assert result["iterations"] == 3

    @pytest.mark.asyncio
    async def test_iterator_max_iterations(self):
        engine = MagicMock(spec=AgentEngine)
        wf_engine = WorkflowEngine(engine)

        result = await wf_engine._execute_iterator_node(
            WorkflowNode(
                id="iter",
                type=NodeType.ITERATOR,
                name="loop",
                config={
                    "collection": "data",
                    "transform": "item",
                    "max_iterations": 3,
                },
            ),
            {"data": list(range(10))},
            "user-1",
            set(),
        )
        assert result["iterations"] == 3

    @pytest.mark.asyncio
    async def test_iterator_identity_transform(self):
        engine = MagicMock(spec=AgentEngine)
        wf_engine = WorkflowEngine(engine)

        result = await wf_engine._execute_iterator_node(
            WorkflowNode(
                id="iter",
                type=NodeType.ITERATOR,
                name="loop",
                config={
                    "collection": "items",
                    "transform": "item",
                },
            ),
            {"items": ["a", "b", "c"]},
            "user-1",
            set(),
        )
        assert result["results"] == ["a", "b", "c"]
