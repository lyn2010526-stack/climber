"""Tests for the Pregel visual-workflow facade."""

from __future__ import annotations

from app.core.agent_engine import AgentEngine
from app.core.engine.pregel.workflow import PregelWorkflowAdapter
from app.workflow import NodeType, WorkflowNode


def _make_engine() -> AgentEngine:
    return AgentEngine.__new__(AgentEngine)


def _linear_flow(node_executor) -> PregelWorkflowAdapter:
    adapter = PregelWorkflowAdapter(
        _make_engine(),
        node_executor=node_executor,
    )
    return adapter


async def test_linear_workflow_updates_state_and_collects_outputs() -> None:
    adapter = _linear_flow(
        lambda node, inputs: {"result": f"{node.name}:{inputs.get('input')}"}
    )
    nodes = [
        {"id": "in", "type": "input", "data": {"label": "Input"}},
        {"id": "mid", "type": "llm", "data": {"label": "Transform", "model": "test-model"}},
        {"id": "out", "type": "output", "data": {"label": "Output"}},
    ]
    edges = [
        {"source": "in", "target": "mid"},
        {"source": "mid", "target": "out"},
    ]
    result = await adapter.run(nodes, edges, {"input": "hello"})
    assert result["status"] == "completed"
    assert result["node_results"]["in"]["output"] == {"input": "hello"}
    assert result["node_results"]["mid"]["output"] == {"result": "Transform:hello"}
    assert result["outputs"]["Output"] == {"result": "Output:hello"}


async def test_conditional_branch_selects_true_side() -> None:
    adapter = _linear_flow(
        lambda node, inputs: {
            "condition_result": inputs.get("value") == "yes",
            "value": inputs.get("value"),
        }
    )
    nodes = [
        {"id": "in", "type": "input", "data": {}},
        {"id": "cond", "type": "condition", "data": {}},
        {"id": "yes", "type": "tool", "data": {}},
        {"id": "no", "type": "tool", "data": {}},
        {"id": "out", "type": "output", "data": {}},
    ]
    edges = [
        {"source": "in", "target": "cond"},
        {"source": "cond", "target": "yes", "sourceHandle": "true"},
        {"source": "cond", "target": "no", "sourceHandle": "false"},
        {"source": "yes", "target": "out"},
        {"source": "no", "target": "out"},
    ]
    result = await adapter.run(nodes, edges, {"value": "yes"})
    assert result["status"] == "completed"
    assert "cond" in result["node_results"]
    assert "yes" in result["node_results"]
    assert "no" not in result["node_results"]


async def test_conditional_branch_selects_false_side() -> None:
    adapter = _linear_flow(
        lambda node, inputs: {
            "condition_result": inputs.get("value") == "yes",
            "value": inputs.get("value"),
        }
    )
    nodes = [
        {"id": "in", "type": "input", "data": {}},
        {"id": "cond", "type": "condition", "data": {}},
        {"id": "yes", "type": "tool", "data": {}},
        {"id": "no", "type": "tool", "data": {}},
        {"id": "out", "type": "output", "data": {}},
    ]
    edges = [
        {"source": "in", "target": "cond"},
        {"source": "cond", "target": "yes", "sourceHandle": "true"},
        {"source": "cond", "target": "no", "sourceHandle": "false"},
        {"source": "no", "target": "out"},
        {"source": "yes", "target": "out"},
    ]
    result = await adapter.run(nodes, edges, {"value": "no"})
    assert result["status"] == "completed"
    assert "cond" in result["node_results"]
    assert "no" in result["node_results"]
    assert "yes" not in result["node_results"]


async def test_run_captures_node_failure() -> None:
    adapter = _linear_flow(
        lambda node, inputs: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    nodes = [
        {"id": "in", "type": "input", "data": {}},
        {"id": "bad", "type": "tool", "data": {}},
    ]
    edges = [{"source": "in", "target": "bad"}]
    result = await adapter.run(nodes, edges, {"input": "x"})
    assert result["status"] == "failed"
    assert "boom" in result["error"]


def test_exposes_workflow_engine_for_agent_settings() -> None:
    adapter = PregelWorkflowAdapter(_make_engine())
    assert adapter.workflow_engine is not None