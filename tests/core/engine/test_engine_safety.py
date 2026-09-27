"""Engine safety-layer regression tests.

Pins the PRODUCTION tool-call permission contract implemented in
app/core/engine/validation.py (the object actually used by AgentEngine,
see agent_engine.py:29 and engine/__init__.py:30). The 4-layer chain is:

    PLAN read-only gate -> permission_rules -> permission overlay -> schema -> sandbox

Cross-validation (Round 4/5) found the original suite pinned the dead
duplicate app/core/engine/safety.py (zero production references); this
file was redirected to the production object. ASK results are dicts
({"requires_approval": True, ...}), not bare strings.
"""

from __future__ import annotations

import pytest

from app.core.engine.validation import _FILE_TOOLS, validate_tool_call
from app.core.permission_rules import get_default_config
from app.core.security_sandbox import (
    AgentMode,
    PermissionLevel,
    PermissionOverlay,
    PermissionRule,
    SandboxConfig,
    SecuritySandbox,
)
from app.core.session import AgentSession


class _FakeTool:
    def __init__(self, parameters: dict | None = None):
        self.parameters = parameters


class _FakeRegistry:
    def __init__(self, tools: dict[str, _FakeTool]):
        self._tools = tools

    def get_tool(self, name: str) -> _FakeTool | None:
        return self._tools.get(name)


@pytest.fixture
def session() -> AgentSession:
    s = AgentSession(session_id="s1", agent_id="a1", user_id="u1")
    s.permission_config = get_default_config()
    return s


@pytest.fixture
def overlay() -> PermissionOverlay:
    return PermissionOverlay()


@pytest.fixture
def sandbox() -> SecuritySandbox:
    return SecuritySandbox(SandboxConfig(workdir="/tmp/sandbox"))


@pytest.fixture
def registry() -> _FakeRegistry:
    return _FakeRegistry({"read_file": _FakeTool({"properties": {"path": {"type": "string"}}})})


# --- PLAN mode read-only enforcement -----------------------------------------


def test_plan_mode_blocks_command_tools(session: AgentSession, sandbox: SecuritySandbox, overlay: PermissionOverlay, registry: _FakeRegistry) -> None:
    ok, reason = validate_tool_call(session, "run_command", {"command": "ls"}, sandbox=sandbox, permission_overlay=overlay, agent_mode=AgentMode.PLAN, tool_registry=registry)
    assert not ok
    assert "read-only" in reason


def test_plan_mode_blocks_file_write(session: AgentSession, sandbox: SecuritySandbox, overlay: PermissionOverlay, registry: _FakeRegistry) -> None:
    ok, reason = validate_tool_call(session, "write_file", {"path": "/tmp/x.py"}, sandbox=sandbox, permission_overlay=overlay, agent_mode=AgentMode.PLAN, tool_registry=registry)
    assert not ok
    assert "read-only" in reason


def test_plan_mode_allows_read_tools(session: AgentSession, sandbox: SecuritySandbox, registry: _FakeRegistry) -> None:
    # PLAN gate lets read-only tools pass; overlay must still allow the read.
    overlay = PermissionOverlay()
    overlay.set_defaults([PermissionRule("read", "*", PermissionLevel.ALLOW)])
    ok, reason = validate_tool_call(session, "read_file", {"path": str(sandbox.config.workdir)}, sandbox=sandbox, permission_overlay=overlay, agent_mode=AgentMode.PLAN, tool_registry=registry)
    assert ok, reason


# --- permission_rules layer (production default config) -----------------------


def test_permission_rules_deny_hazard_command(session: AgentSession, registry: _FakeRegistry) -> None:
    # Default config DENYs "run_command rm -rf *" at the rules layer.
    ok, reason = validate_tool_call(session, "run_command", {"command": "rm -rf *"}, tool_registry=registry)
    assert not ok
    assert "Permission denied by rules" in reason


def test_permission_rules_ask_web_search_returns_approval_dict(session: AgentSession, registry: _FakeRegistry) -> None:
    # Default config ASKs for web_search -> dict result, not bare string.
    ok, result = validate_tool_call(session, "web_search", {"query": "x"}, tool_registry=registry)
    assert not ok
    assert isinstance(result, dict)
    assert result.get("requires_approval") is True


def test_permission_rules_allow_read_file(session: AgentSession, sandbox: SecuritySandbox, registry: _FakeRegistry) -> None:
    ok, reason = validate_tool_call(session, "read_file", {"path": str(sandbox.config.workdir)}, sandbox=sandbox, tool_registry=registry)
    assert ok, reason


# --- Permission overlay enforcement -----------------------------------------


def test_overlay_deny_blocks(session: AgentSession, sandbox: SecuritySandbox, registry: _FakeRegistry) -> None:
    overlay = PermissionOverlay()
    overlay.set_defaults([PermissionRule("read", "*", PermissionLevel.DENY)])
    ok, reason = validate_tool_call(session, "read_file", {"path": "/tmp/x"}, sandbox=sandbox, permission_overlay=overlay, tool_registry=registry)
    assert not ok
    assert "Permission denied" in reason


def test_overlay_ask_requires_approval(session: AgentSession, sandbox: SecuritySandbox, registry: _FakeRegistry) -> None:
    overlay = PermissionOverlay()
    overlay.set_defaults([PermissionRule("read", "*", PermissionLevel.ASK)])
    ok, result = validate_tool_call(session, "read_file", {"path": "/tmp/x"}, sandbox=sandbox, permission_overlay=overlay, tool_registry=registry)
    assert not ok
    assert isinstance(result, dict)
    assert result.get("requires_approval") is True


def test_overlay_allow_passes(session: AgentSession, sandbox: SecuritySandbox, registry: _FakeRegistry) -> None:
    overlay = PermissionOverlay()
    overlay.set_defaults([PermissionRule("read", "*", PermissionLevel.ALLOW)])
    ok, reason = validate_tool_call(session, "read_file", {"path": str(sandbox.config.workdir)}, sandbox=sandbox, permission_overlay=overlay, tool_registry=registry)
    assert ok, reason


# --- Approved-tool-call cache bypasses permission checks ----------------------


def test_approved_tool_call_bypasses_overlay(session: AgentSession, sandbox: SecuritySandbox, registry: _FakeRegistry) -> None:
    # A previously approved tool call (by exact serialized key) skips the
    # permission layers and goes straight to schema+sandbox checks.
    # NOTE: session._approved_tool_calls is lazily created by the engine
    # (agent_engine.py:717-720 uses getattr/setattr), so seed it here.
    overlay = PermissionOverlay()
    overlay.set_defaults([PermissionRule("read", "*", PermissionLevel.DENY)])
    import json
    key = "read_file:" + json.dumps({"path": str(sandbox.config.workdir)}, sort_keys=True)
    session._approved_tool_calls = {key}
    ok, reason = validate_tool_call(session, "read_file", {"path": str(sandbox.config.workdir)}, sandbox=sandbox, permission_overlay=overlay, tool_registry=registry)
    assert ok, reason


# --- Command sandbox enforcement ---------------------------------------------


def test_sandbox_blocks_hazard_command(session: AgentSession, registry: _FakeRegistry) -> None:
    # Production: the DEFAULT permission_rules layer already DENYs
    # "rm -rf *" (permission_rules.py get_default_config), so the call is
    # rejected at the rules layer before ever reaching the sandbox.
    ok, reason = validate_tool_call(session, "run_command", {"command": "rm -rf /"}, tool_registry=registry)
    assert not ok
    assert "Permission denied by rules" in reason


def test_sandbox_blocks_non_allowlist_command(session: AgentSession, overlay: PermissionOverlay, registry: _FakeRegistry) -> None:
    sandbox = SecuritySandbox(SandboxConfig(workdir="/tmp/sandbox"))
    ok, _reason = validate_tool_call(session, "run_command", {"command": "evilbinary --x"}, sandbox=sandbox, permission_overlay=overlay, tool_registry=registry)
    assert not ok


# --- Schema validation enforcement -------------------------------------------


def test_schema_validation_catches_bad_arg_type(session: AgentSession, sandbox: SecuritySandbox, overlay: PermissionOverlay, registry: _FakeRegistry) -> None:
    overlay.set_defaults([PermissionRule("read", "*", PermissionLevel.ALLOW)])
    ok, reason = validate_tool_call(session, "read_file", {"path": 123}, sandbox=sandbox, permission_overlay=overlay, tool_registry=registry)
    assert not ok
    assert "must be string" in reason


# --- FILE_TOOLS metadata ------------------------------------------------------


def test_file_tools_metadata_maps_modes() -> None:
    assert _FILE_TOOLS["read_file"] == ("path", "read")
    assert _FILE_TOOLS["write_file"] == ("path", "write")
    # The real tool is list_files(directory); the table used to name a
    # "list_directory" that was never registered.
    assert _FILE_TOOLS["list_files"] == ("directory", "read")
    assert "list_directory" not in _FILE_TOOLS
