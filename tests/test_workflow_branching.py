"""Conditional branching regression tests (audit item P2-22).

The visual editor used to persist ``condition: (e as any).condition`` instead of
``sourceHandle``, so the branch label the backend reads was always empty. With
no branch label neither the true nor the false edge matched, ``skip_targets``
stayed empty and *both* branches executed. These tests pin the fixed contract:

* the editor payload carries ``sourceHandle`` (mirrored to ``condition``),
* a true condition runs the true branch and skips the false branch,
* the pre-fix payload shape is proven to run both branches, so the regression
  cannot come back unnoticed,
* the engine normalises branch labels written by other creators.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.core import AgentEvent, AgentEventType
from app.core.workflow_executor import build_workflow_from_graph
from app.workflow import NodeStatus, NodeType, Workflow, WorkflowEdge, WorkflowNode
from app.workflow.engine import WorkflowEngine, _normalise_branch_label

REPO_ROOT = Path(__file__).resolve().parents[1]
EDITOR_SOURCE = REPO_ROOT / "frontend-react" / "src" / "components" / "workflow" / "WorkflowEditor.tsx"

BRANCH_LABELS = ("true", "false")


class _RecordingAgentEngine:
    """Minimal AgentEngine stand-in that records which LLM nodes ran."""

    def __init__(self, replies: dict[str, str] | None = None, default: str = "yes") -> None:
        self.replies = replies or {}
        self.default = default
        self.executed: list[str] = []

    def _reply_for(self, agent_id: str) -> str:
        node_id = agent_id.removeprefix("workflow-")
        return self.replies.get(node_id, self.default)

    def create_session(self, **kwargs: Any) -> Any:
        return kwargs

    async def run(self, session: Any, message: str):
        agent_id = session["agent_id"]
        self.executed.append(agent_id)
        yield AgentEvent(type=AgentEventType.TEXT, data={"content": self._reply_for(agent_id)})
        yield AgentEvent(type=AgentEventType.DONE, data={"tokens_used": 0})


#: Distinct text per branch node so the merged end-node output shows which
#: branch actually produced it.
BRANCH_REPLIES = {"classify": "yes", "true_branch": "FROM_TRUE", "false_branch": "FROM_FALSE"}


def _editor_graph(edge_branch_field: str) -> tuple[list[dict], list[dict]]:
    """Build a graph in the shape the visual editor saves.

    Args:
        edge_branch_field: ``"sourceHandle"`` for the fixed editor payload,
            anything else for a payload that carries no branch label at all.
    """
    nodes: list[dict] = [
        {"id": "start", "type": "input", "data": {"label": "Input", "variable_name": "input"}},
        {
            "id": "classify",
            "type": "llm",
            "data": {"label": "Classify", "model": "gpt-4", "system_prompt": "classify"},
        },
        {
            "id": "gate",
            "type": "condition",
            "data": {
                "label": "Gate",
                "variable": "classify.response",
                "operator": "equals",
                "expected_value": "yes",
            },
        },
        {"id": "true_branch", "type": "llm", "data": {"label": "True", "model": "gpt-4"}},
        {"id": "false_branch", "type": "llm", "data": {"label": "False", "model": "gpt-4"}},
        {"id": "out", "type": "output", "data": {"label": "Out", "format": "text"}},
    ]

    def edge(edge_id: str, source: str, target: str, branch: str) -> dict:
        payload: dict[str, Any] = {"id": edge_id, "source": source, "target": target}
        payload[edge_branch_field] = branch
        return payload

    edges: list[dict] = [
        edge("e1", "start", "classify", ""),
        edge("e2", "classify", "gate", ""),
        edge("e3", "gate", "true_branch", "true"),
        edge("e4", "gate", "false_branch", "false"),
        edge("e5", "true_branch", "out", ""),
        edge("e6", "false_branch", "out", ""),
    ]
    return nodes, edges


async def _run_graph(nodes: list[dict], edges: list[dict], replies: dict[str, str] | None = None):
    engine = _RecordingAgentEngine(replies=replies if replies is not None else BRANCH_REPLIES)
    workflow = build_workflow_from_graph(nodes, edges)
    result = await WorkflowEngine(engine).execute(workflow, user_inputs={})
    return workflow, result, engine


def _branching_workflow(true_label: str, false_label: str) -> Workflow:
    """Build the same gate graph directly as ``Workflow``/``WorkflowEdge``.

    Used for the representations that do not travel through the visual editor
    graph mapping: the API/template ``condition`` field and namespaced handle ids.
    """
    return Workflow(
        name="gate",
        nodes=[
            WorkflowNode(id="classify", type=NodeType.LLM, name="Classify"),
            WorkflowNode(
                id="gate",
                type=NodeType.CONDITION,
                name="Gate",
                config={"variable": "classify.response", "operator": "equals", "value": "yes"},
            ),
            WorkflowNode(id="true_branch", type=NodeType.LLM, name="True"),
            WorkflowNode(id="false_branch", type=NodeType.LLM, name="False"),
        ],
        edges=[
            WorkflowEdge(source="classify", target="gate"),
            WorkflowEdge(source="gate", target="true_branch", condition=true_label),
            WorkflowEdge(source="gate", target="false_branch", condition=false_label),
        ],
    )


class TestEditorPersistsBranchLabel:
    """The editor must send the field the backend reads."""

    def test_editor_writes_source_handle(self) -> None:
        source = EDITOR_SOURCE.read_text(encoding="utf-8")
        assert "sourceHandle" in source, "editor must persist the React Flow sourceHandle"
        assert "(e as any).condition" not in source, "the as-any cast must be gone"
        assert "sourceHandle: branch" in source

    def test_editor_mirrors_branch_onto_condition(self) -> None:
        source = EDITOR_SOURCE.read_text(encoding="utf-8")
        assert "condition: branch" in source, "API-created graphs read condition"

    def test_graph_built_from_editor_payload_carries_conditions(self) -> None:
        nodes, edges = _editor_graph("sourceHandle")
        workflow = build_workflow_from_graph(nodes, edges)
        by_target = {e.target: e.condition for e in workflow.edges}
        assert by_target["true_branch"] == "true"
        assert by_target["false_branch"] == "false"
        assert by_target["classify"] == ""


class TestBranchSelection:
    """A real condition must select exactly one branch."""

    async def test_true_branch_runs_and_false_branch_is_skipped(self) -> None:
        nodes, edges = _editor_graph("sourceHandle")
        workflow, result, engine = await _run_graph(nodes, edges)

        assert result.status == "completed"
        assert "workflow-true_branch" in engine.executed
        assert "workflow-false_branch" not in engine.executed

        statuses = {n.id: n.status for n in workflow.nodes}
        assert statuses["true_branch"] == NodeStatus.COMPLETED
        assert statuses["false_branch"] == NodeStatus.SKIPPED
        assert workflow.get_node("false_branch").output is None

    async def test_false_branch_runs_and_true_branch_is_skipped(self) -> None:
        nodes, edges = _editor_graph("sourceHandle")
        workflow, result, engine = await _run_graph(
            nodes, edges, replies={**BRANCH_REPLIES, "classify": "no"}
        )

        assert result.status == "completed"
        assert "workflow-false_branch" in engine.executed
        assert "workflow-true_branch" not in engine.executed
        assert workflow.get_node("true_branch").status == NodeStatus.SKIPPED

    async def test_pre_fix_payload_runs_both_branches(self) -> None:
        """The old editor payload saved no branch label, so both branches ran.

        This is the regression guard: if skipping ever stops working, this test
        and the one above converge and the bug is visible.
        """
        nodes, edges = _editor_graph("sourceHandle")
        for edge in edges:
            edge.pop("sourceHandle", None)

        workflow, result, engine = await _run_graph(nodes, edges)

        assert result.status == "completed"
        assert "workflow-true_branch" in engine.executed
        assert "workflow-false_branch" in engine.executed
        assert {e.condition for e in workflow.get_successors("gate")} == {""}

    async def test_joined_output_comes_from_taken_branch_only(self) -> None:
        nodes, edges = _editor_graph("sourceHandle")
        _, result, _ = await _run_graph(nodes, edges)

        merged = result.outputs["Out"]
        assert merged["response"] == "FROM_TRUE"


class TestBranchLabelNormalisation:
    """Other creators spell the branch label differently."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("true", "true"),
            ("True", "true"),
            (" TRUE ", "true"),
            (True, "true"),
            ("cond-true", "true"),
            ("true-branch", "true"),
            ("false", "false"),
            ("FALSE", "false"),
            (False, "false"),
            ("cond_false", "false"),
            ("", ""),
            (None, ""),
            ("always", ""),
            ("falsey", ""),
        ],
    )
    def test_normalise_branch_label(self, raw: Any, expected: str) -> None:
        assert _normalise_branch_label(raw) == expected

    async def test_namespaced_handle_id_still_branches(self) -> None:
        """A handle id such as ``cond-true`` is normalised on read."""
        built = _branching_workflow(true_label="gate-true", false_label="gate-false")
        result = await WorkflowEngine(_RecordingAgentEngine(BRANCH_REPLIES)).execute(built, user_inputs={})

        assert result.status == "completed"
        assert built.get_node("false_branch").status == NodeStatus.SKIPPED

    async def test_explicit_condition_edges_still_branch(self) -> None:
        """The API/template representation (``condition``) branches identically.

        Both creators converge on ``WorkflowEdge.condition``; only the graph
        dict -> ``WorkflowEdge`` mapping differs.
        """
        built = _branching_workflow(true_label="true", false_label="false")
        result = await WorkflowEngine(_RecordingAgentEngine(BRANCH_REPLIES)).execute(built, user_inputs={})

        assert result.status == "completed"
        assert built.get_node("true_branch").status == NodeStatus.COMPLETED
        assert built.get_node("false_branch").status == NodeStatus.SKIPPED

    async def test_unconditional_edges_are_never_skipped(self) -> None:
        workflow = Workflow(
            name="linear",
            nodes=[
                WorkflowNode(id="start", type=NodeType.START, name="Start"),
                WorkflowNode(
                    id="gate",
                    type=NodeType.CONDITION,
                    name="Gate",
                    config={"variable": "start.flag", "operator": "equals", "value": "yes"},
                ),
                WorkflowNode(id="after", type=NodeType.END, name="After"),
            ],
            edges=[WorkflowEdge(source="start", target="gate"), WorkflowEdge(source="gate", target="after")],
        )
        result = await WorkflowEngine(_RecordingAgentEngine()).execute(workflow, user_inputs={"flag": "no"})
        assert result.status == "completed"
        assert workflow.get_node("after").status == NodeStatus.COMPLETED
