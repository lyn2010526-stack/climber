"""Tests for the workflow engine."""

from __future__ import annotations

import pytest

from app.workflow import (
    NodeStatus,
    NodeType,
    Workflow,
    WorkflowEdge,
    WorkflowNode,
)
from app.workflow.engine import safe_eval, safe_exec


class TestSafeEval:
    """Tests for safe_eval function."""

    def test_simple_expression(self):
        assert safe_eval("1 + 2", {}) == 3

    def test_with_variables(self):
        assert safe_eval("x + y", {"x": 10, "y": 20}) == 30

    def test_string_operations(self):
        assert safe_eval('name + " world"', {"name": "hello"}) == "hello world"

    def test_len_function(self):
        assert safe_eval("len(items)", {"items": [1, 2, 3]}) == 3

    def test_max_function(self):
        assert safe_eval("max(a, b)", {"a": 5, "b": 10}) == 10

    def test_min_function(self):
        assert safe_eval("min(a, b)", {"a": 5, "b": 10}) == 5

    def test_sum_function(self):
        assert safe_eval("sum(items)", {"items": [1, 2, 3]}) == 6

    def test_comparison(self):
        assert safe_eval("x > y", {"x": 10, "y": 5}) is True

    def test_equality(self):
        assert safe_eval("x == y", {"x": 10, "y": 10}) is True

    def test_boolean_and(self):
        assert safe_eval("a and b", {"a": True, "b": False}) is False

    def test_boolean_or(self):
        assert safe_eval("a or b", {"a": True, "b": False}) is True

    def test_ternary_expression(self):
        result = safe_eval("a if a > b else b", {"a": 10, "b": 5})
        assert result == 10

    def test_string_format(self):
        result = safe_eval('f"hello {name}"', {"name": "world"})
        assert result == "hello world"

    def test_nested_expression(self):
        assert safe_eval("(a + b) * c", {"a": 2, "b": 3, "c": 4}) == 20

    def test_type_conversion(self):
        assert safe_eval("int(x) + float(y)", {"x": "10", "y": "3.5"}) == 13.5

    def test_safe_eval_forbids_import(self):
        with pytest.raises((ValueError, NameError)):
            safe_eval("__import__('os')", {})

    def test_safe_eval_forbids_getattr(self):
        with pytest.raises((ValueError, NameError)):
            safe_eval("getattr(obj, '__class__')", {"obj": object()})

    def test_safe_eval_rejects_unsafe_nodes(self):
        with pytest.raises(ValueError):
            safe_eval("[x for x in items if (x := 5)]", {"items": [1, 2, 3]})

    def test_safe_eval_allows_builtins(self):
        result = safe_eval("len(items) + max_val", {"items": [1, 2, 3], "max_val": 10})
        assert result == 13


class TestSafeExec:
    """Tests for safe_exec function."""

    def test_simple_assignment(self):
        result = safe_exec("result = x + y", {"x": 10, "y": 20})
        assert result["result"] == 30

    def test_augmented_assignment(self):
        result = safe_exec("result = 10\nresult += 5", {})
        assert result["result"] == 15

    def test_multiple_statements(self):
        result = safe_exec("a = 1\nb = 2\nresult = a + b", {})
        assert result["result"] == 3

    def test_for_loop(self):
        result = safe_exec(
            "result = 0\nfor i in items:\n    result += i",
            {"items": [1, 2, 3]},
        )
        assert result["result"] == 6

    def test_if_statement(self):
        result = safe_exec(
            "if x > 5:\n    result = 'big'\nelse:\n    result = 'small'",
            {"x": 10},
        )
        assert result["result"] == "big"

    def test_if_statement_false_branch(self):
        result = safe_exec(
            "if x > 5:\n    result = 'big'\nelse:\n    result = 'small'",
            {"x": 3},
        )
        assert result["result"] == "small"

    def test_while_loop(self):
        result = safe_exec(
            "result = 0\ni = 0\nwhile i < 5:\n    result += i\n    i += 1",
            {},
        )
        assert result["result"] == 10

    def test_break_in_loop(self):
        result = safe_exec(
            "result = 0\nfor i in range(10):\n    if i == 5:\n        break\n    result += i",
            {},
        )
        assert result["result"] == 10

    def test_continue_in_loop(self):
        result = safe_exec(
            "result = 0\nfor i in range(10):\n    if i % 2 == 0:\n        continue\n    result += i",
            {},
        )
        assert result["result"] == 25

    def test_list_comp(self):
        result = safe_exec("result = [x * 2 for x in items]", {"items": [1, 2, 3]})
        assert result["result"] == [2, 4, 6]

    def test_dict_comp(self):
        result = safe_exec(
            "result = {k: v * 2 for k, v in d.items()}",
            {"d": {"a": 1, "b": 2}},
        )
        assert result["result"] == {"a": 2, "b": 4}

    def test_assert_passes(self):
        result = safe_exec("assert x > 0\nresult = 'ok'", {"x": 5})
        assert result["result"] == "ok"

    def test_assert_fails(self):
        with pytest.raises(AssertionError):
            safe_exec("assert x < 0", {"x": 5})

    def test_pass_statement(self):
        result = safe_exec("pass\nresult = 'done'", {})
        assert result["result"] == "done"

    def test_raise_statement(self):
        with pytest.raises(Exception):
            safe_exec("raise ValueError('test')", {})

    def test_forbids_private_function_def(self):
        with pytest.raises(ValueError):
            safe_exec("def _private():\n    pass\nresult = 'done'", {})

    def test_forbids_unsafe_import(self):
        with pytest.raises((ValueError, AttributeError)):
            safe_exec("import os", {})

    def test_allows_safe_import(self):
        result = safe_exec("result = {'a': 1}.get('a')", {})
        assert result["result"] == 1

    def test_forbids_class_def(self):
        with pytest.raises(ValueError):
            safe_exec("class Foo: pass", {})

    def test_allows_builtin_functions(self):
        result = safe_exec("result = len([1, 2, 3])", {})
        assert result["result"] == 3


class TestWorkflow:
    """Tests for Workflow model."""

    def test_create_workflow(self):
        wf = Workflow(name="test", description="A test workflow")
        assert wf.name == "test"
        assert wf.description == "A test workflow"
        assert wf.nodes == []
        assert wf.edges == []

    def test_get_node(self):
        node = WorkflowNode(type=NodeType.START, name="Start")
        wf = Workflow(name="test", nodes=[node])
        assert wf.get_node(node.id) == node

    def test_get_node_nonexistent(self):
        wf = Workflow(name="test")
        assert wf.get_node("nonexistent") is None

    def test_get_predecessors(self):
        n1 = WorkflowNode(type=NodeType.START, name="Start")
        n2 = WorkflowNode(type=NodeType.END, name="End")
        wf = Workflow(
            name="test",
            nodes=[n1, n2],
            edges=[WorkflowEdge(source=n1.id, target=n2.id)],
        )
        assert n1.id in wf.get_predecessors(n2.id)

    def test_get_successors(self):
        n1 = WorkflowNode(type=NodeType.START, name="Start")
        n2 = WorkflowNode(type=NodeType.END, name="End")
        edge = WorkflowEdge(source=n1.id, target=n2.id)
        wf = Workflow(
            name="test",
            nodes=[n1, n2],
            edges=[edge],
        )
        result = wf.get_successors(n1.id)
        assert len(result) == 1
        assert result[0].target == n2.id

    def test_topological_sort(self):
        start = WorkflowNode(type=NodeType.START, name="Start")
        llm = WorkflowNode(type=NodeType.LLM, name="LLM")
        end = WorkflowNode(type=NodeType.END, name="End")
        wf = Workflow(
            name="test",
            nodes=[start, llm, end],
            edges=[
                WorkflowEdge(source=start.id, target=llm.id),
                WorkflowEdge(source=llm.id, target=end.id),
            ],
        )
        layers = wf.topological_sort()
        assert len(layers) == 3

    def test_topological_sort_parallel(self):
        start = WorkflowNode(type=NodeType.START, name="Start")
        llm1 = WorkflowNode(type=NodeType.LLM, name="LLM1")
        llm2 = WorkflowNode(type=NodeType.LLM, name="LLM2")
        end = WorkflowNode(type=NodeType.END, name="End")
        wf = Workflow(
            name="test",
            nodes=[start, llm1, llm2, end],
            edges=[
                WorkflowEdge(source=start.id, target=llm1.id),
                WorkflowEdge(source=start.id, target=llm2.id),
                WorkflowEdge(source=llm1.id, target=end.id),
                WorkflowEdge(source=llm2.id, target=end.id),
            ],
        )
        layers = wf.topological_sort()
        assert len(layers) == 3

    def test_topological_sort_cycle_raises(self):
        n1 = WorkflowNode(type=NodeType.LLM, name="N1")
        n2 = WorkflowNode(type=NodeType.LLM, name="N2")
        wf = Workflow(
            name="test",
            nodes=[n1, n2],
            edges=[
                WorkflowEdge(source=n1.id, target=n2.id),
                WorkflowEdge(source=n2.id, target=n1.id),
            ],
        )
        with pytest.raises(ValueError, match="Cycle"):
            wf.topological_sort()


class TestWorkflowEngineConditionEvaluation:
    """Tests for condition evaluation in WorkflowEngine."""

    def test_evaluate_condition_equals(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        assert engine._evaluate_condition("test", "equals", "test") is True
        assert engine._evaluate_condition("test", "equals", "other") is False

    def test_evaluate_condition_not_equals(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        assert engine._evaluate_condition("test", "not_equals", "other") is True
        assert engine._evaluate_condition("test", "not_equals", "test") is False

    def test_evaluate_condition_contains(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        assert engine._evaluate_condition("hello world", "contains", "world") is True
        assert engine._evaluate_condition("hello world", "contains", "xyz") is False

    def test_evaluate_condition_not_contains(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        assert engine._evaluate_condition("hello world", "not_contains", "xyz") is True
        assert engine._evaluate_condition("hello world", "not_contains", "world") is False

    def test_evaluate_condition_starts_with(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        assert engine._evaluate_condition("hello world", "starts_with", "hello") is True
        assert engine._evaluate_condition("hello world", "starts_with", "world") is False

    def test_evaluate_condition_ends_with(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        assert engine._evaluate_condition("hello world", "ends_with", "world") is True
        assert engine._evaluate_condition("hello world", "ends_with", "hello") is False

    def test_evaluate_condition_not_empty(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        assert engine._evaluate_condition("hello", "not_empty", "") is True
        assert engine._evaluate_condition("  ", "not_empty", "") is False
        assert engine._evaluate_condition("", "not_empty", "") is False

    def test_evaluate_condition_empty(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        assert engine._evaluate_condition("", "empty", "") is True
        assert engine._evaluate_condition("  ", "empty", "") is True
        assert engine._evaluate_condition("hello", "empty", "") is False

    def test_evaluate_condition_greater_than(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        assert engine._evaluate_condition("10", "greater_than", "5") is True
        assert engine._evaluate_condition("5", "greater_than", "10") is False

    def test_evaluate_condition_less_than(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        assert engine._evaluate_condition("5", "less_than", "10") is True
        assert engine._evaluate_condition("10", "less_than", "5") is False

    def test_evaluate_condition_greater_than_invalid(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        assert engine._evaluate_condition("abc", "greater_than", "5") is False

    def test_evaluate_condition_regex(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        assert engine._evaluate_condition("hello123", "regex", r"\d+") is True
        assert engine._evaluate_condition("hello", "regex", r"\d+") is False

    def test_evaluate_condition_regex_invalid(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        assert engine._evaluate_condition("test", "regex", r"[invalid") is False

    def test_evaluate_condition_none_actual(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        assert engine._evaluate_condition(None, "equals", "") is True

    def test_evaluate_condition_unknown_operator(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        assert engine._evaluate_condition("a", "unknown_op", "a") is True
        assert engine._evaluate_condition("a", "unknown_op", "b") is False


class TestWorkflowEngineResolveInputs:
    """Tests for input resolution."""

    def test_resolve_inputs_from_predecessors(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        n1 = WorkflowNode(type=NodeType.START, name="Start", output={"key": "value"})
        n2 = WorkflowNode(type=NodeType.LLM, name="LLM", inputs={})
        wf = Workflow(
            name="test",
            nodes=[n1, n2],
            edges=[WorkflowEdge(source=n1.id, target=n2.id)],
        )
        resolved = engine._resolve_inputs(n2, wf)
        assert resolved["key"] == "value"

    def test_resolve_inputs_with_explicit_refs(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        n1 = WorkflowNode(type=NodeType.START, name="Start", output={"result": "hello"})
        n2 = WorkflowNode(type=NodeType.LLM, name="LLM", inputs={"input": f"{n1.id}.result"})
        wf = Workflow(
            name="test",
            nodes=[n1, n2],
            edges=[WorkflowEdge(source=n1.id, target=n2.id)],
        )
        resolved = engine._resolve_inputs(n2, wf)
        assert resolved["input"] == "hello"

    def test_resolve_inputs_non_dict_output(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        n1 = WorkflowNode(type=NodeType.START, name="Start", output="plain string")
        n2 = WorkflowNode(type=NodeType.LLM, name="LLM", inputs={})
        wf = Workflow(
            name="test",
            nodes=[n1, n2],
            edges=[WorkflowEdge(source=n1.id, target=n2.id)],
        )
        resolved = engine._resolve_inputs(n2, wf)
        assert resolved[n1.id] == "plain string"


class TestWorkflowEngineTemplateRendering:
    """Tests for template rendering."""

    def test_render_template(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        result = engine._render_template("Hello {{name}}!", {"name": "World"})
        assert result == "Hello World!"

    def test_render_template_multiple_vars(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        result = engine._render_template(
            "{{greeting}} {{name}}",
            {"greeting": "Hello", "name": "World"},
        )
        assert result == "Hello World"

    def test_render_template_none_value(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        result = engine._render_template("Value: {{val}}", {"val": None})
        assert result == "Value: "


class TestWorkflowEngineVariableResolution:
    """Tests for variable resolution."""

    def test_resolve_variable_simple(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        result = engine._resolve_variable("key", {"key": "value"})
        assert result == "value"

    def test_resolve_variable_dotted(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        result = engine._resolve_variable("parent.child", {"parent": {"child": "value"}})
        assert result == "value"

    def test_resolve_variable_empty(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        result = engine._resolve_variable("", {"key": "value"})
        assert result is None


class TestWorkflowEngineCollectResults:
    """Tests for result collection."""

    def test_collect_results(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        n1 = WorkflowNode(type=NodeType.START, name="Start", output={"result": "ok"})
        n1.status = NodeStatus.COMPLETED
        wf = Workflow(name="test", nodes=[n1])
        results = engine._collect_results(wf)
        assert n1.id in results
        assert results[n1.id]["name"] == "Start"

    def test_collect_results_skips_none(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        n1 = WorkflowNode(type=NodeType.START, name="Start")
        n1.status = NodeStatus.PENDING
        wf = Workflow(name="test", nodes=[n1])
        results = engine._collect_results(wf)
        assert n1.id not in results


class TestWorkflowEngineFinalOutput:
    """Tests for final output extraction."""

    def test_get_final_output_end_nodes(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        end = WorkflowNode(type=NodeType.END, name="End", output={"result": "done"})
        end.status = NodeStatus.COMPLETED
        wf = Workflow(name="test", nodes=[end])
        result = engine._get_final_output(wf)
        assert result == {"End": {"result": "done"}}

    def test_get_final_output_no_end_nodes(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        n1 = WorkflowNode(type=NodeType.LLM, name="LLM", output={"result": "done"})
        n1.status = NodeStatus.COMPLETED
        wf = Workflow(name="test", nodes=[n1])
        result = engine._get_final_output(wf)
        assert result == {"result": {"result": "done"}, "node": "LLM"}

    def test_get_final_output_empty(self):
        from app.workflow.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        wf = Workflow(name="test", nodes=[])
        result = engine._get_final_output(wf)
        assert result == {}
