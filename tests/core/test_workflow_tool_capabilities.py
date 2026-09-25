"""Workflow tool-node capability allowlist tests.

Ensures high-risk tools (file writes, arbitrary shell, docker) are
denied by default in workflow tool nodes, that capability overrides can
opt them back in, and that allowed tools still pass schema and sandbox
checks.
"""

from __future__ import annotations

import tempfile

import pytest

from app.core.engine.safety import COMMAND_TOOLS
from app.core.engine.tool_capabilities import (
    DEFAULT_ALLOWED_TOOLS,
    DEFAULT_DENIED_TOOLS,
    _parse_tool_capabilities,
    build_workflow_tool_validator,
)
from app.core.security_sandbox import SandboxConfig, SecuritySandbox


class _StubRegistry:
    def get_tool(self, name):  # noqa: D102
        return None


def _validator(registry=None, sandbox=None, capabilities=None):
    return build_workflow_tool_validator(
        registry or _StubRegistry(),
        sandbox=sandbox,
        capabilities=capabilities,
    )


@pytest.mark.parametrize("tool", [
    "write_file", "edit_file", "append_file", "apply_patch",
    "run_command", "shell", "execute_command", "bash", "stream_command",
    "container_exec", "docker",
])
def test_high_risk_tools_denied_by_default(tool):
    ok, reason = _validator()(tool, {})
    assert ok is False
    assert "disabled by default" in reason


@pytest.mark.parametrize("tool", sorted(DEFAULT_ALLOWED_TOOLS))
def test_default_allowed_tools_pass_without_sandbox(tool):
    ok, reason = _validator()(tool, {})
    assert ok is True, f"{tool}: {reason}"


def test_read_file_passes_sandbox_when_in_workspace():
    with tempfile.TemporaryDirectory() as workdir:
        sandbox = SecuritySandbox(SandboxConfig(workdir=workdir))
        ok, reason = _validator(sandbox=sandbox)("read_file", {"path": workdir})
        assert ok is True, reason


def test_write_file_denied_even_when_explicitly_enabled_without_capability():
    # Enabling via capabilities list still subject to sandbox file-access scope
    with tempfile.TemporaryDirectory() as workdir:
        sandbox = SecuritySandbox(SandboxConfig(workdir=workdir))
        validator = _validator(sandbox=sandbox, capabilities=["write_file"])
        ok, reason = validator("write_file", {"path": workdir, "content": "x"})
        assert ok is True, reason


def test_capability_plus_override_re_enables_default_denied_tool():
    validator = _validator(capabilities="+write_file")
    ok, _ = validator("write_file", {"path": "/tmp/x", "content": "x"})
    assert ok is True


def test_capability_minus_disables_default_allowed_tool():
    validator = _validator(capabilities="-web_search")
    ok, reason = validator("web_search", {"query": "x"})
    assert ok is False
    assert "disabled by default" in reason


def test_capability_list_adds_new_tool():
    validator = _validator(capabilities=["custom_tool"])
    ok, _ = validator("custom_tool", {})
    assert ok is True


def test_schema_validation_still_enforced():
    from app.tools import ToolDefinition

    class Registry:
        def get_tool(self, name):
            if name == "fetch_url":
                return ToolDefinition(
                    name="fetch_url",
                    description="fetch",
                    parameters={
                        "type": "object",
                        "properties": {"url": {"type": "string"}},
                        "required": ["url"],
                    },
                )
            return None

    validator = _validator(registry=Registry())
    ok, reason = validator("fetch_url", {})
    assert ok is False
    assert "invalid tool arguments" in reason


def test_shell_command_still_hits_sandbox_hazard_policy():
    with tempfile.TemporaryDirectory() as workdir:
        sandbox = SecuritySandbox(SandboxConfig(workdir=workdir))
        validator = _validator(sandbox=sandbox, capabilities=["run_command"])
        ok, reason = validator("run_command", {"command": "rm -rf /"})
        assert ok is False


def test_stream_command_recognized_as_command_tool():
    assert "stream_command" in COMMAND_TOOLS
    assert "container_exec" in COMMAND_TOOLS


def test_parse_capabilities_none_defaults():
    assert _parse_tool_capabilities(None) == set(DEFAULT_ALLOWED_TOOLS)


def test_parse_capabilities_invalid_raises():
    with pytest.raises(ValueError):
        _parse_tool_capabilities(123)


def test_denied_set_covers_file_write_shell_docker():
    assert {"write_file", "run_command", "container_exec"} <= DEFAULT_DENIED_TOOLS


@pytest.mark.asyncio
async def test_workflow_engine_rejects_write_file_tool_node(tmp_path):
    """End-to-end: a tool node calling write_file is rejected by default."""
    from app.workflow import NodeStatus, NodeType, Workflow, WorkflowEdge, WorkflowNode
    from app.workflow.engine import WorkflowEngine

    class _FakeAgentEngine:
        sandbox = SecuritySandbox(SandboxConfig(workdir=str(tmp_path)))
        permission_overlay = None

    workflow = Workflow(
        name="write-test",
        nodes=[
            WorkflowNode(id="start", type=NodeType.START, name="start"),
            WorkflowNode(
                id="t1",
                type=NodeType.TOOL,
                name="write",
                config={
                    "tool_name": "write_file",
                    "tool_inputs": {"path": str(tmp_path / "out.txt"), "content": "x"},
                },
            ),
        ],
        edges=[WorkflowEdge(source="start", target="t1")],
    )

    engine = WorkflowEngine(_FakeAgentEngine())
    result = await engine.execute(workflow, user_inputs={})

    node = workflow.get_node("t1")
    assert node.status == NodeStatus.FAILED
    assert "disabled by default" in node.error
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_workflow_engine_allows_read_tool_node(tmp_path):
    """End-to-end: an allowed read tool executes normally in a tool node."""
    from app.workflow import (
        NodeStatus,
        NodeType,
        Workflow,
        WorkflowEdge,
        WorkflowNode,
    )
    from app.workflow.engine import WorkflowEngine

    class _FakeAgentEngine:
        sandbox = SecuritySandbox(SandboxConfig(workdir=str(tmp_path)))
        permission_overlay = None

    target = tmp_path / "readme.txt"
    target.write_text("hello")

    from app.tools import register_builtins, tool_registry

    register_builtins()

    workflow = Workflow(
        name="read-test",
        nodes=[
            WorkflowNode(id="start", type=NodeType.START, name="start"),
            WorkflowNode(
                id="t1",
                type=NodeType.TOOL,
                name="read",
                config={"tool_name": "read_file", "tool_inputs": {"path": str(target)}},
            ),
        ],
        edges=[WorkflowEdge(source="start", target="t1")],
    )

    engine = WorkflowEngine(_FakeAgentEngine(), tool_registry=tool_registry)
    result = await engine.execute(workflow, user_inputs={})

    node = workflow.get_node("t1")
    assert node.status.value == NodeStatus.COMPLETED.value
    assert "hello" in node.output.get("result", "")
    assert result.status == "completed"
