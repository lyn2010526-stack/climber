"""Command-tool classification regression tests.

``app/core/engine/validation.py`` owns the command-tool set that drives three
security decisions: the PLAN-mode read-only gate, the permission-overlay
execute/read action choice, and the sandbox command check. The native
execution tools registered in ``app/tools/native_tools.py`` (``native_run``,
``process_video``, ``process_image``) spawn a subprocess from a caller-supplied
``command`` argument but were absent from that set, so all three layers treated
them as benign reads.

Pinned here:
- every tool that executes a caller-supplied command is classified as a
  command tool by ``is_command_tool`` (single source of truth)
- the previously-classified tools are unchanged
- the classification is shared, not duplicated: the legacy
  ``app/core/engine/safety.py`` module and ``permission_rules`` read the same
  set instead of holding their own literals
"""

from __future__ import annotations

from typing import Any

import pytest

from app.core.engine.validation import _COMMAND_TOOLS, is_command_tool, validate_tool_call
from app.core.session import AgentSession

# Tools registered by app/tools/native_tools.py that execute a
# caller-supplied "command" argument through a subprocess.
NATIVE_COMMAND_TOOLS = ["native_run", "process_video", "process_image"]

# Classified before this fix; behavior must not change.
PREEXISTING_COMMAND_TOOLS = ["run_command", "shell", "execute_command", "bash"]


class _FakeTool:
    def __init__(self, parameters: dict[str, Any] | None = None) -> None:
        self.parameters = parameters or {}


class _FakeRegistry:
    def __init__(self, tools: dict[str, _FakeTool]) -> None:
        self._tools = tools

    def get_tool(self, name: str) -> _FakeTool | None:
        return self._tools.get(name)


class _StubSandbox:
    """Records the checks the chain asked for, approving both."""

    def __init__(self) -> None:
        self.commands: list[str] = []
        self.files: list[tuple[str, str]] = []

    def validate_command(self, command: str) -> tuple[bool, str]:
        self.commands.append(command)
        return True, "OK"

    def validate_file_access(self, path: str, mode: str) -> tuple[bool, str]:
        self.files.append((path, mode))
        return True, "OK"


@pytest.fixture
def session() -> AgentSession:
    """Session with no permission rules, so the layer under test is reached."""
    s = AgentSession(session_id="cmd-class", agent_id="a1", user_id="u1")
    s.permission_config = None
    return s


@pytest.fixture
def registry() -> _FakeRegistry:
    return _FakeRegistry(
        {
            "native_run": _FakeTool({"properties": {"command": {"type": "string"}}}),
            "process_video": _FakeTool({"properties": {"command": {"type": "string"}}}),
            "process_image": _FakeTool({"properties": {"command": {"type": "string"}}}),
            "run_command": _FakeTool({"properties": {"command": {"type": "string"}}}),
            "read_file": _FakeTool({"properties": {"path": {"type": "string"}}}),
        }
    )


def _allow_overlay(action: str) -> Any:
    from app.core.security_sandbox import PermissionLevel, PermissionOverlay, PermissionRule

    overlay = PermissionOverlay()
    overlay.set_defaults(
        [PermissionRule(action=action, resource_pattern="*", level=PermissionLevel.ALLOW)]
    )
    return overlay


# ─── classification set ─────────────────────────────────────────────────────


@pytest.mark.parametrize("tool_name", NATIVE_COMMAND_TOOLS + PREEXISTING_COMMAND_TOOLS)
def test_execution_tools_are_classified_as_command_tools(tool_name: str) -> None:
    assert is_command_tool(tool_name) is True
    assert tool_name in _COMMAND_TOOLS


@pytest.mark.parametrize("tool_name", ["read_file", "list_files", "web_search", "grep", ""])
def test_non_execution_tools_are_not_command_tools(tool_name: str) -> None:
    assert is_command_tool(tool_name) is False


def test_classification_is_shared_not_duplicated() -> None:
    """The legacy safety module must not keep its own drifting copy."""
    from app.core.engine import safety

    assert safety.COMMAND_TOOLS is _COMMAND_TOOLS
    assert safety.FILE_TOOLS == __import__(
        "app.core.engine.validation", fromlist=["_FILE_TOOLS"]
    )._FILE_TOOLS


# ─── layer 1: PLAN-mode read-only gate ──────────────────────────────────────


@pytest.mark.parametrize("tool_name", NATIVE_COMMAND_TOOLS)
def test_plan_mode_denies_native_execution_tools(
    tool_name: str, session: AgentSession, registry: _FakeRegistry
) -> None:
    from app.core.security_sandbox import AgentMode

    allowed, reason = validate_tool_call(
        session,
        tool_name,
        {"command": "echo hi"},
        sandbox=_StubSandbox(),
        permission_overlay=_allow_overlay("execute"),
        agent_mode=AgentMode.PLAN,
        tool_registry=registry,
    )
    assert allowed is False
    assert "read-only" in reason


def test_plan_mode_still_denies_preexisting_command_tools(
    session: AgentSession, registry: _FakeRegistry
) -> None:
    from app.core.security_sandbox import AgentMode

    allowed, reason = validate_tool_call(
        session,
        "run_command",
        {"command": "echo hi"},
        sandbox=_StubSandbox(),
        permission_overlay=_allow_overlay("execute"),
        agent_mode=AgentMode.PLAN,
        tool_registry=registry,
    )
    assert allowed is False
    assert "read-only" in reason


def test_plan_mode_still_allows_reads(session: AgentSession, registry: _FakeRegistry) -> None:
    from app.core.security_sandbox import AgentMode

    allowed, reason = validate_tool_call(
        session,
        "read_file",
        {"path": "notes.md"},
        sandbox=_StubSandbox(),
        permission_overlay=_allow_overlay("read"),
        agent_mode=AgentMode.PLAN,
        tool_registry=registry,
    )
    assert allowed is True, reason


# ─── layer 2: permission-overlay execute/read action ────────────────────────


@pytest.mark.parametrize("tool_name", NATIVE_COMMAND_TOOLS + PREEXISTING_COMMAND_TOOLS)
def test_overlay_treats_execution_tools_as_execute_action(
    tool_name: str, session: AgentSession, registry: _FakeRegistry
) -> None:
    from app.core.security_sandbox import PermissionLevel, PermissionOverlay, PermissionRule

    overlay = PermissionOverlay()
    overlay.set_defaults(
        [
            PermissionRule(action="read", resource_pattern="*", level=PermissionLevel.ALLOW),
            PermissionRule(action="execute", resource_pattern="*", level=PermissionLevel.ASK),
        ]
    )
    allowed, reason = validate_tool_call(
        session,
        tool_name,
        {"command": "echo hi"},
        sandbox=_StubSandbox(),
        permission_overlay=overlay,
        tool_registry=registry,
    )
    assert allowed is False
    assert isinstance(reason, dict)
    assert reason["action"] == "execute"
    assert reason["requires_approval"] is True


def test_overlay_still_uses_read_action_for_reads(
    session: AgentSession, registry: _FakeRegistry
) -> None:
    from app.core.security_sandbox import PermissionLevel, PermissionOverlay, PermissionRule

    overlay = PermissionOverlay()
    overlay.set_defaults(
        [
            PermissionRule(action="read", resource_pattern="*", level=PermissionLevel.ALLOW),
            PermissionRule(action="execute", resource_pattern="*", level=PermissionLevel.ASK),
        ]
    )
    allowed, reason = validate_tool_call(
        session,
        "read_file",
        {"path": "notes.md"},
        sandbox=_StubSandbox(),
        permission_overlay=overlay,
        tool_registry=registry,
    )
    assert allowed is True, reason


# ─── layer 3: sandbox command check ─────────────────────────────────────────


@pytest.mark.parametrize("tool_name", NATIVE_COMMAND_TOOLS)
def test_native_execution_tools_reach_the_sandbox_command_check(
    tool_name: str, session: AgentSession, registry: _FakeRegistry
) -> None:
    from app.core.security_sandbox import SandboxConfig, SecuritySandbox

    sandbox = SecuritySandbox(SandboxConfig(workdir="/tmp/sandbox"))
    allowed, reason = validate_tool_call(
        session,
        tool_name,
        {"command": "rm -rf /"},
        sandbox=sandbox,
        permission_overlay=_allow_overlay("execute"),
        tool_registry=registry,
    )
    assert allowed is False
    assert reason, "the sandbox must speak for a hazard command"


@pytest.mark.parametrize("tool_name", NATIVE_COMMAND_TOOLS + PREEXISTING_COMMAND_TOOLS)
def test_command_string_is_handed_to_the_sandbox(
    tool_name: str, session: AgentSession, registry: _FakeRegistry
) -> None:
    """The command must reach sandbox.validate_command, not skip the layer."""
    sandbox = _StubSandbox()
    allowed, reason = validate_tool_call(
        session,
        tool_name,
        {"command": "echo hi"},
        sandbox=sandbox,
        permission_overlay=_allow_overlay("execute"),
        tool_registry=registry,
    )
    assert allowed is True, reason
    assert sandbox.commands == ["echo hi"]


def test_safe_native_command_passes_a_live_sandbox(
    session: AgentSession, registry: _FakeRegistry
) -> None:
    from app.core.security_sandbox import SandboxConfig, SecuritySandbox

    sandbox = SecuritySandbox(SandboxConfig(workdir="/tmp/sandbox"))
    allowed, reason = validate_tool_call(
        session,
        "native_run",
        {"command": "echo hi"},
        sandbox=sandbox,
        permission_overlay=_allow_overlay("execute"),
        tool_registry=registry,
    )
    assert allowed is True, reason


def test_native_command_tool_fails_closed_without_a_sandbox(
    session: AgentSession, registry: _FakeRegistry
) -> None:
    """A sandbox failure must refuse execution tools, native ones included."""
    from app.core.security_sandbox import AgentMode

    allowed, reason = validate_tool_call(
        session,
        "native_run",
        {"command": "echo hi"},
        sandbox=None,
        permission_overlay=_allow_overlay("execute"),
        agent_mode=AgentMode.ACT,
        tool_registry=registry,
    )
    assert allowed is False
    assert "failed to initialize" in reason


# ─── permission_rules uses the same classification ──────────────────────────


@pytest.mark.parametrize("tool_name", NATIVE_COMMAND_TOOLS + PREEXISTING_COMMAND_TOOLS)
def test_permission_rules_assess_risk_as_command_execution(tool_name: str) -> None:
    from app.core.permission_rules import PermissionConfig

    assert PermissionConfig().assess_risk(tool_name, {"command": "rm -rf /tmp/x"}) in {
        "high",
        "medium",
    }


def test_permission_rules_high_risk_pattern_applies_to_native_tools() -> None:
    from app.core.permission_rules import PermissionConfig, PermissionMode

    config = PermissionConfig(mode=PermissionMode.AUTO)
    assert config._is_high_risk("process_video", {"command": "rm -rf /"}) is True


def test_permission_rule_pattern_matches_native_command_tools() -> None:
    from app.core.permission_rules import PermissionRule, RuleDecision

    rule = PermissionRule(RuleDecision.DENY, "native_run", "rm -rf *")
    assert rule.matches("native_run", {"command": "rm -rf /tmp/data"}) is True
    assert rule.matches("native_run", {"command": "ls -la"}) is False
