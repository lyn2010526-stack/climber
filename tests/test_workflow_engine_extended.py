"""Extended tests for WorkflowEngine execution methods."""

from __future__ import annotations

import unittest.mock as mock

import pytest

from app.workflow import (
    NodeStatus,
    NodeType,
    Workflow,
    WorkflowNode,
)
from app.workflow.engine import (
    WorkflowEngine,
)


def make_engine():
    """Create a WorkflowEngine without full initialization."""
    engine = WorkflowEngine.__new__(WorkflowEngine)
    engine.agent_engine = mock.MagicMock()
    engine.model_registry = None
    return engine


class TestEvaluateCondition:
    """Tests for condition evaluation."""

    def test_equals_true(self):
        engine = make_engine()
        assert engine._evaluate_condition("hello", "equals", "hello") is True

    def test_equals_false(self):
        engine = make_engine()
        assert engine._evaluate_condition("hello", "equals", "world") is False

    def test_not_equals_true(self):
        engine = make_engine()
        assert engine._evaluate_condition("hello", "not_equals", "world") is True

    def test_not_equals_false(self):
        engine = make_engine()
        assert engine._evaluate_condition("hello", "not_equals", "hello") is False

    def test_contains_true(self):
        engine = make_engine()
        assert engine._evaluate_condition("hello world", "contains", "world") is True

    def test_contains_false(self):
        engine = make_engine()
        assert engine._evaluate_condition("hello world", "contains", "xyz") is False

    def test_not_contains_true(self):
        engine = make_engine()
        assert engine._evaluate_condition("hello world", "not_contains", "xyz") is True

    def test_not_contains_false(self):
        engine = make_engine()
        assert engine._evaluate_condition("hello world", "not_contains", "world") is False

    def test_starts_with_true(self):
        engine = make_engine()
        assert engine._evaluate_condition("hello world", "starts_with", "hello") is True

    def test_starts_with_false(self):
        engine = make_engine()
        assert engine._evaluate_condition("hello world", "starts_with", "world") is False

    def test_ends_with_true(self):
        engine = make_engine()
        assert engine._evaluate_condition("hello world", "ends_with", "world") is True

    def test_ends_with_false(self):
        engine = make_engine()
        assert engine._evaluate_condition("hello world", "ends_with", "hello") is False

    def test_not_empty_true(self):
        engine = make_engine()
        assert engine._evaluate_condition("hello", "not_empty", "") is True

    def test_not_empty_false(self):
        engine = make_engine()
        assert engine._evaluate_condition("", "not_empty", "") is False

    def test_not_empty_whitespace(self):
        engine = make_engine()
        assert engine._evaluate_condition("   ", "not_empty", "") is False

    def test_empty_true(self):
        engine = make_engine()
        assert engine._evaluate_condition("", "empty", "") is True

    def test_empty_false(self):
        engine = make_engine()
        assert engine._evaluate_condition("hello", "empty", "") is False

    def test_greater_than_true(self):
        engine = make_engine()
        assert engine._evaluate_condition("10", "greater_than", "5") is True

    def test_greater_than_false(self):
        engine = make_engine()
        assert engine._evaluate_condition("3", "greater_than", "5") is False

    def test_less_than_true(self):
        engine = make_engine()
        assert engine._evaluate_condition("3", "less_than", "5") is True

    def test_less_than_false(self):
        engine = make_engine()
        assert engine._evaluate_condition("10", "less_than", "5") is False

    def test_greater_than_invalid_number(self):
        engine = make_engine()
        assert engine._evaluate_condition("abc", "greater_than", "5") is False

    def test_less_than_invalid_number(self):
        engine = make_engine()
        assert engine._evaluate_condition("abc", "less_than", "5") is False

    def test_regex_true(self):
        engine = make_engine()
        assert engine._evaluate_condition("hello123", "regex", r"\d+") is True

    def test_regex_false(self):
        engine = make_engine()
        assert engine._evaluate_condition("hello", "regex", r"\d+") is False

    def test_regex_invalid_pattern(self):
        engine = make_engine()
        assert engine._evaluate_condition("hello", "regex", "[invalid") is False

    def test_none_value_defaults_to_empty(self):
        engine = make_engine()
        assert engine._evaluate_condition(None, "equals", "") is True

    def test_unknown_operator_fallback(self):
        engine = make_engine()
        assert engine._evaluate_condition("hello", "unknown_op", "hello") is True

    def test_unknown_operator_fallback_false(self):
        engine = make_engine()
        assert engine._evaluate_condition("hello", "unknown_op", "world") is False


class TestExecuteConditionNode:
    """Tests for _execute_condition_node."""

    def test_without_workflow_context(self):
        engine = make_engine()
        node = WorkflowNode(
            id="cond-1",
            name="Check",
            type=NodeType.CONDITION,
            config={"variable": "status", "operator": "equals", "value": "ok"},
        )
        result = engine._execute_condition_node(node, {"status": "ok"}, workflow=None)
        assert result["condition_result"] is True
        assert result["variable"] == "ok"

    def test_with_workflow_true_branch(self):
        engine = make_engine()
        cond_node = WorkflowNode(
            id="cond-1",
            name="Check",
            type=NodeType.CONDITION,
            config={"variable": "status", "operator": "equals", "value": "ok"},
        )
        true_node = WorkflowNode(id="true-1", name="True Branch", type=NodeType.LLM)
        false_node = WorkflowNode(id="false-1", name="False Branch", type=NodeType.LLM)
        workflow = Workflow(
            id="wf-1",
            name="Test",
            nodes=[cond_node, true_node, false_node],
            edges=[
                {"source": "cond-1", "target": "true-1", "condition": "true"},
                {"source": "cond-1", "target": "false-1", "condition": "false"},
            ],
        )
        result, skip_targets = engine._execute_condition_node(
            cond_node, {"status": "ok"}, workflow=workflow
        )
        assert result["condition_result"] is True
        assert "false-1" in skip_targets
        assert "true-1" not in skip_targets

    def test_with_workflow_false_branch(self):
        engine = make_engine()
        cond_node = WorkflowNode(
            id="cond-2",
            name="Check",
            type=NodeType.CONDITION,
            config={"variable": "status", "operator": "equals", "value": "ok"},
        )
        true_node = WorkflowNode(id="true-2", name="True Branch", type=NodeType.LLM)
        false_node = WorkflowNode(id="false-2", name="False Branch", type=NodeType.LLM)
        workflow = Workflow(
            id="wf-2",
            name="Test",
            nodes=[cond_node, true_node, false_node],
            edges=[
                {"source": "cond-2", "target": "true-2", "condition": "true"},
                {"source": "cond-2", "target": "false-2", "condition": "false"},
            ],
        )
        result, skip_targets = engine._execute_condition_node(
            cond_node, {"status": "fail"}, workflow=workflow
        )
        assert result["condition_result"] is False
        assert "true-2" in skip_targets
        assert "false-2" not in skip_targets

    def test_with_field_config_key(self):
        engine = make_engine()
        node = WorkflowNode(
            id="cond-3",
            name="Check",
            type=NodeType.CONDITION,
            config={"field": "status", "operator": "equals", "value": "ok"},
        )
        result = engine._execute_condition_node(node, {"status": "ok"}, workflow=None)
        assert result["condition_result"] is True


class TestSkipDownstream:
    """Tests for _skip_downstream and _is_reachable_from."""

    def test_skip_downstream_basic(self):
        engine = make_engine()
        cond_node = WorkflowNode(id="cond-s", name="Cond", type=NodeType.CONDITION)
        branch_node = WorkflowNode(id="branch-s", name="Branch", type=NodeType.LLM)
        target1 = WorkflowNode(id="target-s1", name="Target1", type=NodeType.LLM)
        target2 = WorkflowNode(id="target-s2", name="Target2", type=NodeType.LLM)
        workflow = Workflow(
            id="wf-skip",
            name="Test",
            nodes=[cond_node, branch_node, target1, target2],
            edges=[
                {"source": "cond-s", "target": "branch-s"},
                {"source": "branch-s", "target": "target-s1"},
                {"source": "branch-s", "target": "target-s2"},
            ],
        )
        skipped = set()
        engine._skip_downstream("branch-s", "cond-s", workflow, skipped)
        assert "target-s1" in skipped
        assert "target-s2" in skipped

    def test_skip_downstream_reachable_via_other_path(self):
        engine = make_engine()
        cond_node = WorkflowNode(id="cond-r", name="Cond", type=NodeType.CONDITION)
        branch_node = WorkflowNode(id="branch-r", name="Branch", type=NodeType.LLM)
        target1 = WorkflowNode(id="target-r1", name="Target1", type=NodeType.LLM)
        workflow = Workflow(
            id="wf-reach",
            name="Test",
            nodes=[cond_node, branch_node, target1],
            edges=[
                {"source": "cond-r", "target": "branch-r"},
                {"source": "branch-r", "target": "target-r1"},
                {"source": "cond-r", "target": "target-r1"},
            ],
        )
        skipped = set()
        engine._skip_downstream("branch-r", "cond-r", workflow, skipped)
        assert "target-r1" not in skipped

    def test_is_reachable_from_direct(self):
        engine = make_engine()
        n1 = WorkflowNode(id="r1", name="A", type=NodeType.LLM)
        n2 = WorkflowNode(id="r2", name="B", type=NodeType.LLM)
        workflow = Workflow(
            id="wf-r",
            name="Test",
            nodes=[n1, n2],
            edges=[{"source": "r1", "target": "r2"}],
        )
        assert engine._is_reachable_from("r1", "r2", workflow) is True

    def test_is_reachable_from_indirect(self):
        engine = make_engine()
        n1 = WorkflowNode(id="i1", name="A", type=NodeType.LLM)
        n2 = WorkflowNode(id="i2", name="B", type=NodeType.LLM)
        n3 = WorkflowNode(id="i3", name="C", type=NodeType.LLM)
        workflow = Workflow(
            id="wf-i",
            name="Test",
            nodes=[n1, n2, n3],
            edges=[
                {"source": "i1", "target": "i2"},
                {"source": "i2", "target": "i3"},
            ],
        )
        assert engine._is_reachable_from("i1", "i3", workflow) is True

    def test_is_reachable_from_not_connected(self):
        engine = make_engine()
        n1 = WorkflowNode(id="n1", name="A", type=NodeType.LLM)
        n2 = WorkflowNode(id="n2", name="B", type=NodeType.LLM)
        workflow = Workflow(
            id="wf-n",
            name="Test",
            nodes=[n1, n2],
            edges=[],
        )
        assert engine._is_reachable_from("n1", "n2", workflow) is False

    def test_is_reachable_from_exclude_node(self):
        engine = make_engine()
        n1 = WorkflowNode(id="e1", name="A", type=NodeType.LLM)
        n2 = WorkflowNode(id="e2", name="B", type=NodeType.LLM)
        n3 = WorkflowNode(id="e3", name="C", type=NodeType.LLM)
        workflow = Workflow(
            id="wf-e",
            name="Test",
            nodes=[n1, n2, n3],
            edges=[
                {"source": "e1", "target": "e2"},
                {"source": "e2", "target": "e3"},
                {"source": "e1", "target": "e3"},
            ],
        )
        assert engine._is_reachable_from("e1", "e3", workflow, exclude_node="e2") is True


class TestExecuteIteratorNode:
    """Tests for _execute_iterator_node."""

    @pytest.mark.asyncio
    async def test_basic_iteration(self):
        engine = make_engine()
        node = WorkflowNode(
            id="iter-1",
            name="Loop",
            type=NodeType.ITERATOR,
            config={"collection": "items", "transform": "item * 2"},
        )
        result = await engine._execute_iterator_node(
            node, {"items": [1, 2, 3]}, "user-1", set()
        )
        assert result["iterations"] == 3
        assert result["results"] == [2, 4, 6]

    @pytest.mark.asyncio
    async def test_iteration_with_index(self):
        engine = make_engine()
        node = WorkflowNode(
            id="iter-2",
            name="Loop",
            type=NodeType.ITERATOR,
            config={"collection": "items", "transform": "item + index"},
        )
        result = await engine._execute_iterator_node(
            node, {"items": [10, 20, 30]}, "user-1", set()
        )
        assert result["results"] == [10, 21, 32]

    @pytest.mark.asyncio
    async def test_iteration_with_max_limit(self):
        engine = make_engine()
        node = WorkflowNode(
            id="iter-3",
            name="Loop",
            type=NodeType.ITERATOR,
            config={"collection": "items", "transform": "item", "max_iterations": 2},
        )
        result = await engine._execute_iterator_node(
            node, {"items": [1, 2, 3, 4, 5]}, "user-1", set()
        )
        assert result["iterations"] == 2

    @pytest.mark.asyncio
    async def test_iteration_non_list_collection(self):
        engine = make_engine()
        node = WorkflowNode(
            id="iter-4",
            name="Loop",
            type=NodeType.ITERATOR,
            config={"collection": "items", "transform": "item"},
        )
        result = await engine._execute_iterator_node(
            node, {"items": "[1, 2, 3]"}, "user-1", set()
        )
        assert result["iterations"] == 3

    @pytest.mark.asyncio
    async def test_iteration_invalid_json(self):
        engine = make_engine()
        node = WorkflowNode(
            id="iter-5",
            name="Loop",
            type=NodeType.ITERATOR,
            config={"collection": "items", "transform": "item"},
        )
        result = await engine._execute_iterator_node(
            node, {"items": "not json"}, "user-1", set()
        )
        assert result["iterations"] == 0

    @pytest.mark.asyncio
    async def test_iteration_transform_error(self):
        engine = make_engine()
        node = WorkflowNode(
            id="iter-6",
            name="Loop",
            type=NodeType.ITERATOR,
            config={"collection": "items", "transform": "undefined_var"},
        )
        result = await engine._execute_iterator_node(
            node, {"items": [1, 2]}, "user-1", set()
        )
        assert result["iterations"] == 2
        assert "Error" in result["results"][0]

    @pytest.mark.asyncio
    async def test_iteration_custom_item_var(self):
        engine = make_engine()
        node = WorkflowNode(
            id="iter-7",
            name="Loop",
            type=NodeType.ITERATOR,
            config={"collection": "data", "item_var": "x", "transform": "x.upper()"},
        )
        result = await engine._execute_iterator_node(
            node, {"data": ["a", "b", "c"]}, "user-1", set()
        )
        assert result["results"] == ["A", "B", "C"]


class TestExecuteCodeNode:
    """Tests for _execute_code_node."""

    def test_basic_code_execution(self):
        engine = make_engine()
        node = WorkflowNode(
            id="code-1",
            name="Code",
            type=NodeType.CODE,
            config={"code": "result = inputs['x'] + inputs['y']"},
        )
        result = engine._execute_code_node(node, {"x": 10, "y": 20})
        assert "result" in result
        assert "node_id" in result

    def test_code_with_template_rendering(self):
        engine = make_engine()
        node = WorkflowNode(
            id="code-2",
            name="Code",
            type=NodeType.CODE,
            config={"code": "result = {{value}} * 2"},
        )
        result = engine._execute_code_node(node, {"value": 5})
        assert "result" in result
        assert "node_id" in result

    def test_code_error_handling(self):
        engine = make_engine()
        node = WorkflowNode(
            id="code-3",
            name="Code",
            type=NodeType.CODE,
            config={"code": "result = 1 / 0"},
        )
        result = engine._execute_code_node(node, {})
        assert "Error" in result["result"]

    def test_code_no_result_var(self):
        engine = make_engine()
        node = WorkflowNode(
            id="code-4",
            name="Code",
            type=NodeType.CODE,
            config={"code": "x = 42"},
        )
        result = engine._execute_code_node(node, {})
        assert "result" in result


class TestResolveInputs:
    """Tests for _resolve_inputs."""

    def test_auto_merge_predecessor_outputs(self):
        engine = make_engine()
        pred = WorkflowNode(
            id="pred-1",
            name="Pred",
            type=NodeType.LLM,
            output={"response": "hello", "node_id": "pred-1"},
        )
        node = WorkflowNode(
            id="node-1",
            name="Current",
            type=NodeType.LLM,
            inputs={},
        )
        workflow = Workflow(
            id="wf-ri",
            name="Test",
            nodes=[pred, node],
            edges=[{"source": "pred-1", "target": "node-1"}],
        )
        result = engine._resolve_inputs(node, workflow)
        assert result["response"] == "hello"
        assert result["node_id"] == "pred-1"

    def test_explicit_input_references(self):
        engine = make_engine()
        pred = WorkflowNode(
            id="pred-2",
            name="Pred",
            type=NodeType.LLM,
            output={"result": "value1", "extra": "value2"},
        )
        node = WorkflowNode(
            id="node-2",
            name="Current",
            type=NodeType.LLM,
            inputs={"out": "pred-2.result"},
        )
        workflow = Workflow(
            id="wf-ri2",
            name="Test",
            nodes=[pred, node],
            edges=[{"source": "pred-2", "target": "node-2"}],
        )
        result = engine._resolve_inputs(node, workflow)
        assert result["out"] == "value1"

    def test_explicit_reference_without_key(self):
        engine = make_engine()
        pred = WorkflowNode(
            id="pred-3",
            name="Pred",
            type=NodeType.LLM,
            output={"result": "myresult"},
        )
        node = WorkflowNode(
            id="node-3",
            name="Current",
            type=NodeType.LLM,
            inputs={"data": "pred-3"},
        )
        workflow = Workflow(
            id="wf-ri3",
            name="Test",
            nodes=[pred, node],
            edges=[{"source": "pred-3", "target": "node-3"}],
        )
        result = engine._resolve_inputs(node, workflow)
        assert result["data"] == "myresult"

    def test_predecessor_with_non_dict_output(self):
        engine = make_engine()
        pred = WorkflowNode(
            id="pred-4",
            name="Pred",
            type=NodeType.LLM,
            output="plain string",
        )
        node = WorkflowNode(
            id="node-4",
            name="Current",
            type=NodeType.LLM,
            inputs={},
        )
        workflow = Workflow(
            id="wf-ri4",
            name="Test",
            nodes=[pred, node],
            edges=[{"source": "pred-4", "target": "node-4"}],
        )
        result = engine._resolve_inputs(node, workflow)
        assert result["pred-4"] == "plain string"

    def test_no_predecessors(self):
        engine = make_engine()
        node = WorkflowNode(
            id="node-5",
            name="Current",
            type=NodeType.LLM,
            inputs={},
        )
        workflow = Workflow(
            id="wf-ri5",
            name="Test",
            nodes=[node],
            edges=[],
        )
        result = engine._resolve_inputs(node, workflow)
        assert result == {}


class TestResolveVariable:
    """Tests for _resolve_variable."""

    def test_simple_variable(self):
        engine = make_engine()
        assert engine._resolve_variable("name", {"name": "Alice"}) == "Alice"

    def test_dotted_variable(self):
        engine = make_engine()
        assert engine._resolve_variable("node.result", {"node": {"result": 42}}) == 42

    def test_dotted_variable_missing_key(self):
        engine = make_engine()
        assert engine._resolve_variable("node.missing", {"node": {"result": 42}}) is None

    def test_empty_variable(self):
        engine = make_engine()
        assert engine._resolve_variable("", {"name": "Alice"}) is None

    def test_non_dict_parent(self):
        engine = make_engine()
        assert engine._resolve_variable("node.key", {"node": "string"}) == "string"


class TestRenderTemplate:
    """Tests for _render_template."""

    def test_simple_replacement(self):
        engine = make_engine()
        result = engine._render_template("Hello {{name}}!", {"name": "World"})
        assert result == "Hello World!"

    def test_multiple_replacements(self):
        engine = make_engine()
        result = engine._render_template(
            "{{greeting}} {{name}}!", {"greeting": "Hello", "name": "World"}
        )
        assert result == "Hello World!"

    def test_no_placeholders(self):
        engine = make_engine()
        result = engine._render_template("No placeholders", {"name": "World"})
        assert result == "No placeholders"

    def test_none_value(self):
        engine = make_engine()
        result = engine._render_template("Value: {{val}}", {"val": None})
        assert result == "Value: "

    def test_missing_key(self):
        engine = make_engine()
        result = engine._render_template("Hello {{name}}!", {"greeting": "Hi"})
        assert result == "Hello {{name}}!"


class TestCollectResults:
    """Tests for _collect_results."""

    def test_collects_all_outputs(self):
        engine = make_engine()
        n1 = WorkflowNode(
            id="cr-1",
            name="A",
            type=NodeType.LLM,
            output={"result": "ok"},
            status=NodeStatus.COMPLETED,
        )
        n2 = WorkflowNode(
            id="cr-2",
            name="B",
            type=NodeType.LLM,
            output=None,
            status=NodeStatus.PENDING,
        )
        workflow = Workflow(id="wf-cr", name="Test", nodes=[n1, n2], edges=[])
        results = engine._collect_results(workflow)
        assert "cr-1" in results
        assert "cr-2" not in results
        assert results["cr-1"]["output"] == {"result": "ok"}


class TestGetFinalOutput:
    """Tests for _get_final_output."""

    def test_end_nodes_output(self):
        engine = make_engine()
        end = WorkflowNode(
            id="end-1",
            name="End",
            type=NodeType.END,
            output={"result": "final"},
            status=NodeStatus.COMPLETED,
        )
        workflow = Workflow(id="wf-fo", name="Test", nodes=[end], edges=[])
        result = engine._get_final_output(workflow)
        assert result == {"End": {"result": "final"}}

    def test_no_end_nodes(self):
        engine = make_engine()
        n1 = WorkflowNode(
            id="n1",
            name="A",
            type=NodeType.LLM,
            output={"result": "ok"},
            status=NodeStatus.COMPLETED,
        )
        workflow = Workflow(id="wf-fo2", name="Test", nodes=[n1], edges=[])
        result = engine._get_final_output(workflow)
        assert result == {"result": {"result": "ok"}, "node": "A"}

    def test_no_completed_nodes(self):
        engine = make_engine()
        n1 = WorkflowNode(
            id="n2",
            name="A",
            type=NodeType.LLM,
            output=None,
            status=NodeStatus.PENDING,
        )
        workflow = Workflow(id="wf-fo3", name="Test", nodes=[n1], edges=[])
        result = engine._get_final_output(workflow)
        assert result == {}
