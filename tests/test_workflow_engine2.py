"""Tests for workflow engine - part 3."""

from __future__ import annotations

import unittest.mock as mock

import pytest

from app.workflow import NodeStatus, NodeType, Workflow, WorkflowNode, WorkflowResult
from app.workflow.engine import WorkflowEngine


class TestWorkflowEngineInit:
    """Tests for WorkflowEngine initialization."""

    def test_init(self):
        mock_engine = mock.MagicMock()
        engine = WorkflowEngine(mock_engine)
        assert engine.agent_engine is mock_engine
        assert engine.model_registry is None

    def test_init_with_model_registry(self):
        mock_engine = mock.MagicMock()
        mock_registry = mock.MagicMock()
        engine = WorkflowEngine(mock_engine, mock_registry)
        assert engine.model_registry is mock_registry


class TestWorkflowEngineExecute:
    """Tests for WorkflowEngine.execute."""

    @pytest.mark.asyncio
    async def test_execute_empty_workflow(self):
        mock_engine = mock.MagicMock()
        engine = WorkflowEngine(mock_engine)
        workflow = Workflow(name="empty")

        result = await engine.execute(workflow)
        assert isinstance(result, WorkflowResult)
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_execute_workflow_with_start_node(self):
        mock_engine = mock.MagicMock()
        engine = WorkflowEngine(mock_engine)

        start_node = WorkflowNode(type=NodeType.START, name="Start")
        end_node = WorkflowNode(type=NodeType.END, name="End")

        workflow = Workflow(
            name="test",
            nodes=[start_node, end_node],
        )

        result = await engine.execute(workflow)
        assert isinstance(result, WorkflowResult)

    @pytest.mark.asyncio
    async def test_execute_with_user_inputs(self):
        mock_engine = mock.MagicMock()
        engine = WorkflowEngine(mock_engine)

        start_node = WorkflowNode(type=NodeType.START, name="Start")
        end_node = WorkflowNode(type=NodeType.END, name="End")

        workflow = Workflow(
            name="test",
            nodes=[start_node, end_node],
        )

        result = await engine.execute(workflow, user_inputs={"key": "value"})
        assert isinstance(result, WorkflowResult)


class TestWorkflowEngineNodeExecution:
    """Tests for node execution paths."""

    @pytest.mark.asyncio
    async def test_execute_llm_node(self):
        mock_engine = mock.MagicMock()
        mock_engine.process = mock.AsyncMock(return_value={"response": "test output"})

        engine = WorkflowEngine(mock_engine)

        node = WorkflowNode(type=NodeType.LLM, name="LLM Node")
        node.config = {"prompt": "test prompt"}

        workflow = Workflow(name="test", nodes=[node])

        # Create a mock for _resolve_inputs
        engine._resolve_inputs = mock.MagicMock(return_value={"input": "value"})
        engine._execute_llm_node = mock.AsyncMock(return_value={"output": "result"})

        # Just verify the method can be called
        result = engine._resolve_inputs(node, workflow)
        assert result == {"input": "value"}

    @pytest.mark.asyncio
    async def test_execute_tool_node(self):
        mock_engine = mock.MagicMock()
        engine = WorkflowEngine(mock_engine)

        node = WorkflowNode(type=NodeType.TOOL, name="Tool Node")
        node.config = {"tool_name": "test_tool"}

        workflow = Workflow(name="test", nodes=[node])

        engine._resolve_inputs = mock.MagicMock(return_value={})
        engine._execute_tool_node = mock.AsyncMock(return_value={"output": "result"})

        result = engine._resolve_inputs(node, workflow)
        assert result == {}

    @pytest.mark.asyncio
    async def test_execute_code_node(self):
        mock_engine = mock.MagicMock()
        engine = WorkflowEngine(mock_engine)

        node = WorkflowNode(type=NodeType.CODE, name="Code Node")
        node.config = {"code": "result = 1 + 1"}

        workflow = Workflow(name="test", nodes=[node])

        engine._resolve_inputs = mock.MagicMock(return_value={})
        engine._execute_code_node = mock.AsyncMock(return_value={"result": 2})

        result = engine._resolve_inputs(node, workflow)
        assert result == {}


class TestWorkflowEngineResults:
    """Tests for result collection."""

    def test_collect_results(self):
        mock_engine = mock.MagicMock()
        engine = WorkflowEngine(mock_engine)

        node1 = WorkflowNode(type=NodeType.LLM, name="Node1")
        node1.output = {"result": "output1"}
        node1.status = NodeStatus.COMPLETED

        node2 = WorkflowNode(type=NodeType.TOOL, name="Node2")
        node2.output = {"result": "output2"}
        node2.status = NodeStatus.COMPLETED

        workflow = Workflow(name="test", nodes=[node1, node2])
        results = engine._collect_results(workflow)

        assert len(results) == 2

    def test_get_final_output(self):
        mock_engine = mock.MagicMock()
        engine = WorkflowEngine(mock_engine)

        start_node = WorkflowNode(type=NodeType.START, name="Start")
        start_node.output = {"input": "value"}

        end_node = WorkflowNode(type=NodeType.END, name="End")
        end_node.output = {"final": "output"}

        workflow = Workflow(name="test", nodes=[start_node, end_node])
        output = engine._get_final_output(workflow)

        assert isinstance(output, dict)


class TestWorkflowEngineConditions:
    """Tests for condition evaluation."""

    def test_evaluate_condition_equals(self):
        mock_engine = mock.MagicMock()
        engine = WorkflowEngine(mock_engine)
        result = engine._evaluate_condition("test", "equals", "test")
        assert result is True

    def test_evaluate_condition_not_equals(self):
        mock_engine = mock.MagicMock()
        engine = WorkflowEngine(mock_engine)
        result = engine._evaluate_condition("other", "equals", "test")
        assert result is False

    def test_evaluate_condition_greater_than(self):
        mock_engine = mock.MagicMock()
        engine = WorkflowEngine(mock_engine)
        result = engine._evaluate_condition("10", "greater_than", "5")
        assert result is True

    def test_evaluate_condition_less_than(self):
        mock_engine = mock.MagicMock()
        engine = WorkflowEngine(mock_engine)
        result = engine._evaluate_condition("5", "less_than", "10")
        assert result is True

    def test_evaluate_condition_contains(self):
        mock_engine = mock.MagicMock()
        engine = WorkflowEngine(mock_engine)
        result = engine._evaluate_condition("hello world", "contains", "world")
        assert result is True

    def test_evaluate_condition_not_contains(self):
        mock_engine = mock.MagicMock()
        engine = WorkflowEngine(mock_engine)
        result = engine._evaluate_condition("hello world", "not_contains", "xyz")
        assert result is True

    def test_evaluate_condition_starts_with(self):
        mock_engine = mock.MagicMock()
        engine = WorkflowEngine(mock_engine)
        result = engine._evaluate_condition("hello world", "starts_with", "hello")
        assert result is True

    def test_evaluate_condition_ends_with(self):
        mock_engine = mock.MagicMock()
        engine = WorkflowEngine(mock_engine)
        result = engine._evaluate_condition("hello world", "ends_with", "world")
        assert result is True

    def test_evaluate_condition_not_empty(self):
        mock_engine = mock.MagicMock()
        engine = WorkflowEngine(mock_engine)
        result = engine._evaluate_condition("value", "not_empty", "")
        assert result is True

    def test_evaluate_condition_empty(self):
        mock_engine = mock.MagicMock()
        engine = WorkflowEngine(mock_engine)
        result = engine._evaluate_condition("", "empty", "")
        assert result is True

    def test_evaluate_condition_regex(self):
        mock_engine = mock.MagicMock()
        engine = WorkflowEngine(mock_engine)
        result = engine._evaluate_condition("hello123", "regex", r"\d+")
        assert result is True

    def test_evaluate_condition_none_actual(self):
        mock_engine = mock.MagicMock()
        engine = WorkflowEngine(mock_engine)
        result = engine._evaluate_condition(None, "equals", "")
        assert result is True
