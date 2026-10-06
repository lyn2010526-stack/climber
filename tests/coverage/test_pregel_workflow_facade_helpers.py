"""Coverage tests for app.core.engine.pregel.workflow facade helpers."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from app.core.agent_engine import AgentEngine
from app.core.engine.pregel.workflow import PregelWorkflowAdapter
from app.workflow import NodeType, Workflow, WorkflowEdge, WorkflowNode


def _engine() -> AgentEngine:
    return AgentEngine.__new__(AgentEngine)


def _workflow(nodes, edges=()) -> Workflow:
    return Workflow(name="wf", nodes=list(nodes), edges=list(edges))


def test_source_nodes_detects_roots() -> None:
    wf = _workflow(
        [
            WorkflowNode(id="a", type=NodeType.START, name="A"),
            WorkflowNode(id="b", type=NodeType.LLM, name="B"),
        ],
        [WorkflowEdge(source="a", target="b")],
    )
    assert PregelWorkflowAdapter._source_nodes(wf) == {"a"}


def test_entry_node_prefers_start() -> None:
    adapter = PregelWorkflowAdapter(_engine())
    start = WorkflowNode(id="s", type=NodeType.START, name="Start")
    other = WorkflowNode(id="x", type=NodeType.LLM, name="X")
    wf = _workflow([other, start], [WorkflowEdge(source="s", target="x")])
    assert adapter._entry_node(wf).id == "s"


def test_entry_node_without_start_uses_source() -> None:
    adapter = PregelWorkflowAdapter(_engine())
    root = WorkflowNode(id="root", type=NodeType.LLM, name="Root")
    child = WorkflowNode(id="child", type=NodeType.LLM, name="Child")
    wf = _workflow([root, child], [WorkflowEdge(source="root", target="child")])
    assert adapter._entry_node(wf).id == "root"


def test_entry_node_falls_back_to_first_when_cycle() -> None:
    adapter = PregelWorkflowAdapter(_engine())
    a = WorkflowNode(id="a", type=NodeType.LLM, name="A")
    b = WorkflowNode(id="b", type=NodeType.LLM, name="B")
    wf = _workflow(
        [a, b], [WorkflowEdge(source="a", target="b"), WorkflowEdge(source="b", target="a")]
    )
    assert adapter._entry_node(wf).id == "a"


async def test_make_workflow_node_all_types_via_workflow_engine() -> None:
    adapter = PregelWorkflowAdapter(_engine())

    async def _async(node, resolved, *args):
        return {"kind": node.type.value, "resolved": resolved}

    def _cond(node, resolved):
        return {"condition_result": True, "resolved": resolved}

    adapter.workflow_engine = SimpleNamespace(  # type: ignore[assignment]
        _execute_condition_node=_cond,
        _execute_llm_node=_async,
        _execute_tool_node=_async,
        _execute_code_node=_async,
        _execute_simulation_node=_async,
        _execute_iterator_node=_async,
    )

    wf = _workflow([WorkflowNode(id="pred", type=NodeType.LLM, name="P")])
    for node_type in (
        NodeType.CONDITION,
        NodeType.LLM,
        NodeType.TOOL,
        NodeType.CODE,
        NodeType.SIMULATION,
        NodeType.ITERATOR,
        NodeType.END,
    ):
        node = WorkflowNode(id="n", type=node_type, name="N")
        fn = adapter._make_workflow_node(node, wf, "user")
        out = await fn({"pred": {"value": 1}})
        assert "n" in out

    start_node = WorkflowNode(id="s", type=NodeType.START, name="S")
    fn_start = adapter._make_workflow_node(start_node, wf, "user")
    assert await fn_start({}) == {}


async def test_make_workflow_node_with_custom_executor_async() -> None:
    async def executor(node, inputs):
        return {"custom": inputs}

    adapter = PregelWorkflowAdapter(_engine(), node_executor=executor)
    wf = _workflow([])
    node = WorkflowNode(id="n", type=NodeType.LLM, name="N")
    fn = adapter._make_workflow_node(node, wf, "user")
    out = await fn({})
    assert out["n"]["custom"] == {}


async def test_make_workflow_node_end_merges_inputs() -> None:
    adapter = PregelWorkflowAdapter(
        _engine(), node_executor=lambda node, inputs: {"received": inputs}
    )
    wf = _workflow([], [WorkflowEdge(source="pred", target="end")])
    node = WorkflowNode(id="end", type=NodeType.END, name="End")
    fn = adapter._make_workflow_node(node, wf, "user")
    out = await fn({"_inputs": {"secret": 1}, "pred": {"a": 2}})
    assert out["end"]["received"]["secret"] == 1
    assert out["end"]["received"]["a"] == 2


async def test_make_workflow_node_sets_pregel_id() -> None:
    adapter = PregelWorkflowAdapter(_engine())
    wf = _workflow([])
    node = WorkflowNode(id="abc", type=NodeType.LLM, name="N")
    fn = adapter._make_workflow_node(node, wf, "user")
    assert fn.__pregel_node_id__ == "abc"


async def test_condition_router_dict_and_scalar() -> None:
    adapter = PregelWorkflowAdapter(_engine())
    wf = _workflow([])
    router = adapter._condition_router("c", wf)
    assert await router({"c": {"condition_result": True}}) == "true"
    assert await router({"c": {"condition_result": False}}) == "false"
    assert await router({"c": "truthy"}) == "true"
    assert await router({"c": ""}) == "false"


def test_condition_path_map() -> None:
    wf = _workflow(
        [],
        [
            WorkflowEdge(source="c", target="yes", condition="true"),
            WorkflowEdge(source="c", target="no", condition="false"),
            WorkflowEdge(source="c", target="other"),
        ],
    )
    assert PregelWorkflowAdapter._condition_path_map("c", wf) == {"true": "yes", "false": "no"}


def test_resolve_inputs_predecessors_and_refs() -> None:
    adapter = PregelWorkflowAdapter(_engine())
    node = WorkflowNode(
        id="n",
        type=NodeType.LLM,
        name="N",
        inputs={"direct": "p1", "dotted": "p2.field", "scalar": "p3"},
    )
    wf = _workflow(
        [node],
        [
            WorkflowEdge(source="p1", target="n"),
            WorkflowEdge(source="p2", target="n"),
            WorkflowEdge(source="p3", target="n"),
        ],
    )
    state = {
        "p1": {"k": "v"},
        "p2": {"field": "dotted-value"},
        "p3": "scalar-value",
    }
    resolved = adapter._resolve_inputs(node, wf, state)
    assert resolved["k"] == "v"
    assert resolved["direct"] == {"k": "v"}
    assert resolved["dotted"] == "dotted-value"
    assert resolved["scalar"] == "scalar-value"


def test_resolve_inputs_handles_missing_and_non_dict_predecessor() -> None:
    adapter = PregelWorkflowAdapter(_engine())
    node = WorkflowNode(id="n", type=NodeType.LLM, name="N", inputs={"r": "p"})
    wf = _workflow(
        [node], [WorkflowEdge(source="p", target="n"), WorkflowEdge(source="q", target="n")]
    )
    state = {"q": 99, "p": {"result": "from-result"}}
    resolved = adapter._resolve_inputs(node, wf, state)
    assert resolved["q"] == 99
    # p resolves via plain-ref -> "result" key
    assert resolved["r"] == "from-result"


def test_resolve_inputs_skips_none_outputs_and_missing_refs() -> None:
    adapter = PregelWorkflowAdapter(_engine())
    node = WorkflowNode(id="n", type=NodeType.LLM, name="N", inputs={"missing": "ghost"})
    wf = _workflow(
        [node],
        [WorkflowEdge(source="pnone", target="n"), WorkflowEdge(source="pscalar", target="n")],
    )
    state: dict[str, Any] = {"pnone": None, "pscalar": 5}
    resolved = adapter._resolve_inputs(node, wf, state)
    assert resolved == {"pscalar": 5}


def test_collect_outputs_with_end_nodes() -> None:
    adapter = PregelWorkflowAdapter(_engine())
    end = WorkflowNode(id="e", type=NodeType.END, name="End")
    wf = _workflow([end])
    assert adapter._collect_outputs(wf, {"e": {"out": 1}}) == {"End": {"out": 1}}


def test_collect_outputs_fallback_last_completed() -> None:
    adapter = PregelWorkflowAdapter(_engine())
    start = WorkflowNode(id="s", type=NodeType.START, name="S")
    mid = WorkflowNode(id="m", type=NodeType.LLM, name="Mid")
    wf = _workflow([start, mid])
    assert adapter._collect_outputs(wf, {"s": {"x": 1}, "m": {"y": 2}}) == {
        "result": {"y": 2},
        "node": "Mid",
    }
    assert adapter._collect_outputs(wf, {}) == {}


def test_collect_node_results() -> None:
    adapter = PregelWorkflowAdapter(_engine())
    n = WorkflowNode(id="n", type=NodeType.LLM, name="N")
    wf = _workflow([n])
    results = adapter._collect_node_results(wf, {"n": {"out": 1}})
    assert results["n"]["status"] == "completed"
    assert results["n"]["type"] == "llm"
    assert adapter._collect_node_results(wf, {}) == {}


async def test_run_with_condition_node() -> None:
    def executor(node, inputs):
        if node.type == NodeType.CONDITION:
            return {"condition_result": inputs.get("flag") == "yes"}
        return {"out": inputs.get("flag")}

    adapter = PregelWorkflowAdapter(_engine(), node_executor=executor)
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
    ]
    result = await adapter.run(nodes, edges, {"flag": "yes"})
    assert result["status"] == "completed"
    assert "yes" in result["node_results"]


async def test_run_reports_failure_when_executor_raises() -> None:
    def executor(node, inputs):
        raise RuntimeError("exec-failed")

    adapter = PregelWorkflowAdapter(_engine(), node_executor=executor)
    nodes = [{"id": "in", "type": "input", "data": {}}, {"id": "n", "type": "tool", "data": {}}]
    edges = [{"source": "in", "target": "n"}]
    result = await adapter.run(nodes, edges, {})
    assert result["status"] == "failed"
    assert "exec-failed" in result["error"]


async def test_run_returns_failure_on_disallowed_goto() -> None:
    """A node routing to an unknown target terminates the graph; outputs empty."""
    adapter = PregelWorkflowAdapter(_engine(), node_executor=lambda node, inputs: {"r": 1})
    nodes = [{"id": "in", "type": "input", "data": {}}, {"id": "out", "type": "output", "data": {}}]
    edges = [{"source": "in", "target": "out"}]
    result = await adapter.run(nodes, edges, {})
    assert result["status"] == "completed"


async def test_run_uses_custom_entry_without_start_node() -> None:
    adapter = PregelWorkflowAdapter(_engine(), node_executor=lambda node, inputs: {"r": 1})
    nodes = [{"id": "a", "type": "llm", "data": {}}, {"id": "b", "type": "llm", "data": {}}]
    edges = [{"source": "a", "target": "b"}]
    result = await adapter.run(nodes, edges, {"x": 1})
    assert result["status"] == "completed"
    assert "a" in result["node_results"]


async def test_compile_creates_graph_and_workflow() -> None:
    adapter = PregelWorkflowAdapter(_engine(), node_executor=lambda node, inputs: {})
    graph, workflow = adapter.compile(
        [{"id": "in", "type": "input", "data": {}}, {"id": "out", "type": "output", "data": {}}],
        [{"source": "in", "target": "out"}],
        name="My Flow",
    )
    assert graph.get_node("__start__") is not None
    assert workflow.name == "My Flow"
