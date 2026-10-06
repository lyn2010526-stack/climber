"""Coverage tests for app.core.security_sandbox.

Covers permission overlay merge logic, JSON-schema validation, command
hazard/allowlist checks, the AST code sandbox, approval workflow, and the
audit-log system (persistence is exercised against a fake session).
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.core.security_sandbox import (
    HAZARD_COMMANDS,
    AgentMode,
    ApprovalStatus,
    AuditSystem,
    CodeSandbox,
    ExecutionMode,
    PermissionApprovalSystem,
    PermissionLevel,
    PermissionOverlay,
    PermissionRequest,
    PermissionRule,
    SandboxConfig,
    SchemaValidationError,
    SecuritySandbox,
    VerificationResult,
    audit_system,
    intercept_hazards,
    permission_system,
    security_sandbox,
    validate_command_allowlist,
    validate_tool_input,
)

# ── enums & dataclasses ─────────────────────────────────────────────────


def test_enum_values() -> None:
    assert ExecutionMode.SANDBOX.value == "sandbox"
    assert ExecutionMode.FULL_AUTO.value == "full_auto"
    assert AgentMode.PLAN.value == "plan"
    assert AgentMode.ACT.value == "act"
    assert PermissionLevel.DENY.value == "deny"
    assert PermissionLevel.ASK.value == "ask"
    assert PermissionLevel.ALLOW.value == "allow"
    assert ApprovalStatus.PENDING.value == "pending"


def test_permission_rule_defaults() -> None:
    rule = PermissionRule(action="read", resource_pattern="*", level=PermissionLevel.ALLOW)
    assert rule.description == ""


def test_singletons_exist() -> None:
    assert isinstance(security_sandbox, SecuritySandbox)
    assert isinstance(permission_system, PermissionApprovalSystem)
    assert isinstance(audit_system, AuditSystem)
    assert HAZARD_COMMANDS  # non-empty


# ── PermissionOverlay ───────────────────────────────────────────────────


def test_overlay_empty_denies() -> None:
    assert PermissionOverlay().evaluate("read", "/x") is PermissionLevel.DENY


def test_overlay_defaults_match() -> None:
    overlay = PermissionOverlay()
    overlay.set_defaults([PermissionRule("read", "/data/*", PermissionLevel.ALLOW)])
    assert overlay.evaluate("read", "/data/file") is PermissionLevel.ALLOW
    assert overlay.evaluate("write", "/data/file") is PermissionLevel.DENY


def test_overlay_agent_and_user_precedence() -> None:
    overlay = PermissionOverlay()
    overlay.set_defaults([PermissionRule("read", "*", PermissionLevel.DENY)])
    overlay.set_agent_rules("agent1", [PermissionRule("read", "*", PermissionLevel.ASK)])
    overlay.set_user_rules("user1", [PermissionRule("read", "*", PermissionLevel.ALLOW)])

    # user layer wins over agent over defaults
    assert overlay.evaluate("read", "/x", agent_id="agent1", user_id="user1") is (
        PermissionLevel.ALLOW
    )
    # falls through to agent when no user rule for that id
    assert overlay.evaluate("read", "/x", agent_id="agent1") is PermissionLevel.ASK
    # falls through to defaults
    assert overlay.evaluate("read", "/x") is PermissionLevel.DENY


def test_overlay_specificity_tie_break() -> None:
    overlay = PermissionOverlay()
    overlay.set_defaults(
        [
            PermissionRule("read", "*", PermissionLevel.ALLOW),
            PermissionRule("read", "/data/*", PermissionLevel.DENY),
        ]
    )
    # the more specific "/data/*" wins for paths under /data
    assert overlay.evaluate("read", "/data/file") is PermissionLevel.DENY
    assert overlay.evaluate("read", "/other") is PermissionLevel.ALLOW


def test_overlay_priority_helper() -> None:
    assert PermissionOverlay._priority(PermissionLevel.DENY) == 2
    assert PermissionOverlay._priority(PermissionLevel.ASK) == 1
    assert PermissionOverlay._priority(PermissionLevel.ALLOW) == 0
    assert PermissionOverlay._specificity("/a/b/c") == (6, 0)
    assert PermissionOverlay._specificity("/a/*") == (3, -1)
    assert PermissionOverlay._match("/a/*", "/a/b") is True


# ── validate_tool_input ─────────────────────────────────────────────────


def test_validate_tool_input_empty_schema_is_noop() -> None:
    validate_tool_input({}, {"anything": 1})


def test_validate_tool_input_missing_required() -> None:
    with pytest.raises(SchemaValidationError, match="Missing required field: name"):
        validate_tool_input({"required": ["name"]}, {})


def test_validate_tool_input_continues_when_required_present() -> None:
    schema = {"required": ["a", "b"], "properties": {"a": {"type": "integer"}}}
    with pytest.raises(SchemaValidationError, match="Missing required field: b"):
        validate_tool_input(schema, {"a": 1})


def test_validate_tool_input_type_mismatches() -> None:
    schema = {
        "properties": {
            "s": {"type": "string"},
            "i": {"type": "integer"},
            "n": {"type": "number"},
            "b": {"type": "boolean"},
            "a": {"type": "array"},
            "o": {"type": "object"},
        }
    }
    with pytest.raises(SchemaValidationError, match="'s' must be a string"):
        validate_tool_input(schema, {"s": 1})
    with pytest.raises(SchemaValidationError, match="'i' must be an integer"):
        validate_tool_input(schema, {"i": "x"})
    with pytest.raises(SchemaValidationError, match="'n' must be a number"):
        validate_tool_input(schema, {"n": "x"})
    with pytest.raises(SchemaValidationError, match="'b' must be a boolean"):
        validate_tool_input(schema, {"b": 1})
    with pytest.raises(SchemaValidationError, match="'a' must be an array"):
        validate_tool_input(schema, {"a": "x"})
    with pytest.raises(SchemaValidationError, match="'o' must be an object"):
        validate_tool_input(schema, {"o": [1]})


def test_validate_tool_input_accepts_valid_and_ignores_unknown() -> None:
    schema = {"properties": {"s": {"type": "string"}}}
    validate_tool_input(schema, {"s": "ok", "unknown": object()})


# ── SecuritySandbox ─────────────────────────────────────────────────────


def test_security_sandbox_validate_command_hazard() -> None:
    sandbox = SecuritySandbox(SandboxConfig(workdir="/tmp/ws"))
    ok, reason = sandbox.validate_command("sudo rm -rf /")
    assert ok is False
    assert "hazard pattern" in reason


def test_security_sandbox_validate_command_not_allowed() -> None:
    sandbox = SecuritySandbox(SandboxConfig(workdir="/tmp/ws"))
    ok, reason = sandbox.validate_command("foobarbaz --flag")
    assert ok is False
    assert "not in the allowed commands list" in reason


def test_security_sandbox_validate_command_allowed_and_empty() -> None:
    sandbox = SecuritySandbox(SandboxConfig(workdir="/tmp/ws"))
    assert sandbox.validate_command("ls -la") == (True, "OK")
    assert sandbox.validate_command("   ") == (True, "OK")
    # base name is normalised (leading ./ stripped, path components removed)
    assert sandbox.validate_command("./ls")[0] is True


def test_security_sandbox_validate_file_access_blocked_default() -> None:
    sandbox = SecuritySandbox(SandboxConfig(workdir="/tmp/ws"))
    ok, reason = sandbox.validate_file_access("/etc/passwd")
    assert ok is False
    assert "blocked list" in reason


def test_security_sandbox_validate_file_access_wildcard_block() -> None:
    sandbox = SecuritySandbox(SandboxConfig(workdir="/tmp/ws", blocked_paths=["/home/*/.ssh"]))
    ok, reason = sandbox.validate_file_access("/home/bob/.ssh/id_rsa")
    assert ok is False
    assert "blocked list" in reason


def test_security_sandbox_validate_file_access_outside(tmp_path: Any) -> None:
    sandbox = SecuritySandbox(SandboxConfig(workdir=str(tmp_path)))
    ok, reason = sandbox.validate_file_access("/tmp/definitely-not-allowed-xyz")
    assert ok is False
    assert "outside allowed directories" in reason


def test_security_sandbox_validate_file_access_ok(tmp_path: Any) -> None:
    target = tmp_path / "f.txt"
    target.write_text("hi", encoding="utf-8")
    sandbox = SecuritySandbox(SandboxConfig(workdir=str(tmp_path)))
    assert sandbox.validate_file_access(str(target)) == (True, "OK")


def test_security_sandbox_validate_file_access_too_large(tmp_path: Any) -> None:
    target = tmp_path / "big.txt"
    target.write_text("hello", encoding="utf-8")
    sandbox = SecuritySandbox(SandboxConfig(workdir=str(tmp_path), max_file_size_mb=0))
    ok, reason = sandbox.validate_file_access(str(target))
    assert ok is False
    assert "File too large" in reason


def test_security_sandbox_validate_file_access_write_mode(tmp_path: Any) -> None:
    # write mode skips the size check
    target = tmp_path / "big.txt"
    target.write_text("hello", encoding="utf-8")
    sandbox = SecuritySandbox(SandboxConfig(workdir=str(tmp_path), max_file_size_mb=0))
    assert sandbox.validate_file_access(str(target), mode="write") == (True, "OK")


def test_security_sandbox_is_within() -> None:
    assert SecuritySandbox._is_within("/a/b/c", "/a") is True
    assert SecuritySandbox._is_within("/a", "/a") is True
    assert SecuritySandbox._is_within("/other", "/a") is False


def test_security_sandbox_is_within_commonpath_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(paths: Any) -> str:
        raise ValueError("cannot mix paths")

    monkeypatch.setattr("app.core.security_sandbox.os.path.commonpath", boom)
    assert SecuritySandbox._is_within("/a", "/b") is False


def test_security_sandbox_sanitize_output() -> None:
    sandbox = SecuritySandbox(SandboxConfig(workdir="/tmp/ws", max_output_size_kb=1))
    assert sandbox.sanitize_output("short") == "short"
    big = "a" * 5000
    out = sandbox.sanitize_output(big)
    assert out.endswith("KB limit]")
    assert out.startswith("a" * 1024)


def test_security_sandbox_sanitize_output_multibyte() -> None:
    sandbox = SecuritySandbox(SandboxConfig(workdir="/tmp/ws", max_output_size_kb=1))
    out = sandbox.sanitize_output("é" * 600)
    assert "Output truncated" in out


# ── validate_command_allowlist ──────────────────────────────────────────


def test_allowlist_empty_and_quotes() -> None:
    assert validate_command_allowlist("")[0] is False
    ok, reason = validate_command_allowlist("echo 'unterminated")
    assert ok is False
    assert "unclosed quote" in reason
    ok, reason = validate_command_allowlist('echo "unterminated')
    assert ok is False
    assert "unclosed quote" in reason


def test_allowlist_not_permitted() -> None:
    ok, reason = validate_command_allowlist("foobarbaz x")
    assert ok is False
    assert "not in the allowed commands list" in reason


def test_allowlist_rm_dangerous_arguments() -> None:
    for cmd in ("rm -rf x", "rm -fr x", "rm --recursive --force x", "rm --force-recursive x"):
        ok, reason = validate_command_allowlist(cmd)
        assert ok is False, cmd
        assert "Dangerous arguments" in reason


def test_allowlist_rm_safe_and_other_allowed() -> None:
    assert validate_command_allowlist("rm file.txt") == (True, "OK")
    assert validate_command_allowlist("git status") == (True, "OK")
    assert validate_command_allowlist("./git status") == (True, "OK")


# ── CodeSandbox / intercept_hazards ─────────────────────────────────────


def test_code_sandbox_forbidden_module_import() -> None:
    result = CodeSandbox().verify("import os")
    assert result.allowed is False
    assert "Forbidden module: os" in result.reason


def test_code_sandbox_forbidden_import_from() -> None:
    result = CodeSandbox().verify("from socket import socket")
    assert result.allowed is False
    assert "Forbidden module: socket" in result.reason


def test_code_sandbox_forbidden_dunder_attribute() -> None:
    result = CodeSandbox().verify("x = obj.__subclasses__")
    assert result.allowed is False
    assert "Forbidden dunder: __subclasses__" in result.reason


def test_code_sandbox_forbidden_function_call() -> None:
    result = CodeSandbox().verify("eval('1 + 1')")
    assert result.allowed is False
    assert "Forbidden function: eval" in result.reason


def test_code_sandbox_clean_code_allowed() -> None:
    result = CodeSandbox().verify("x = 1\ndef f(y):\n    return y + x\n")
    assert result.allowed is True
    assert result.reason == ""


def test_code_sandbox_walks_all_safe_node_kinds() -> None:
    code = "import json\nfrom json import dumps\nfrom . import sibling\nx = obj.attr\nprint(1)\n"
    result = CodeSandbox().verify(code)
    assert result.allowed is True


def test_code_sandbox_syntax_error() -> None:
    result = CodeSandbox().verify("def broken(:\n")
    assert result.allowed is False
    assert result.reason.startswith("Syntax error:")


def test_preflight_script_rejects_empty_or_non_string() -> None:
    sandbox = CodeSandbox()
    assert sandbox.preflight_script(None).allowed is False  # type: ignore[arg-type]
    assert sandbox.preflight_script("   ").allowed is False
    assert sandbox.preflight_script("x = 1").allowed is True


def test_verification_result_defaults() -> None:
    result = VerificationResult(True)
    assert result.reason == ""


def test_intercept_hazards() -> None:
    ok, reason = intercept_hazards("foobarbaz")
    assert ok is False
    assert "not in the allowed commands" in reason

    ok, reason = intercept_hazards("cat foo.py", code="import os")
    assert ok is False
    assert "Forbidden module" in reason

    assert intercept_hazards("cat foo.py", code="x = 1") == (True, "OK")
    assert intercept_hazards("ls") == (True, "OK")


# ── PermissionApprovalSystem ────────────────────────────────────────────


def test_permission_request_and_grant_flow() -> None:
    system = PermissionApprovalSystem()
    req = system.request_permission("s1", "access_path", "/secret", risk_level="high")
    assert isinstance(req, PermissionRequest)
    assert req.status is ApprovalStatus.PENDING
    assert req.risk_level == "high"
    assert system.get_pending_requests() == [req]

    granted = system.grant_permission(req.id, temporary=True)
    assert granted is not None
    assert granted.status is ApprovalStatus.GRANTED
    assert granted.resolved_at is not None
    assert system.check_permission("s1", "access_path") is True
    assert system.check_permission("s2", "access_path") is False

    system.revoke_permission("s1", "access_path")
    assert system.check_permission("s1", "access_path") is False
    # revoking a non-existent grant is a no-op
    system.revoke_permission("s1", "never-granted")


def test_permission_grant_and_deny_missing_request() -> None:
    system = PermissionApprovalSystem()
    assert system.grant_permission("missing") is None
    assert system.deny_permission("missing") is None


def test_permission_deny_and_filtering() -> None:
    system = PermissionApprovalSystem()
    r1 = system.request_permission("s1", "run_command", "ls")
    r2 = system.request_permission("s2", "run_command", "pwd")
    denied = system.deny_permission(r1.id)
    assert denied is not None
    assert denied.status is ApprovalStatus.DENIED
    assert system.get_pending_requests() == [r2]
    assert system.get_pending_requests(session_id="s2") == [r2]
    assert system.get_pending_requests(session_id="s1") == []

    system.clear_session("s2")
    assert system._active_grants.get("s2") is None


def test_permission_grant_non_temporary() -> None:
    system = PermissionApprovalSystem()
    req = system.request_permission("s1", "access_path", "/x")
    granted = system.grant_permission(req.id, temporary=False)
    assert granted is not None
    assert granted.temporary is False


def test_permission_multiple_grants_same_session() -> None:
    system = PermissionApprovalSystem()
    first = system.request_permission("s1", "access_path", "/a")
    second = system.request_permission("s1", "run_command", "ls")
    system.grant_permission(first.id)
    system.grant_permission(second.id)  # session already present in _active_grants
    assert system.check_permission("s1", "access_path") is True
    assert system.check_permission("s1", "run_command") is True
    assert system._active_grants["s1"] == ["access_path", "run_command"]


# ── AuditSystem ─────────────────────────────────────────────────────────


def _silence_persist(audit: AuditSystem, monkeypatch: pytest.MonkeyPatch) -> None:
    def noop(coro: Any) -> None:
        coro.close()

    monkeypatch.setattr(audit, "_spawn_persist", noop)


async def test_audit_log_entries_and_queries(monkeypatch: pytest.MonkeyPatch) -> None:
    audit = AuditSystem()
    _silence_persist(audit, monkeypatch)

    audit.log_file_operation("s1", "read", "/a.py")
    audit.log_file_operation("s1", "delete", "/b.py", details={"diff": "x"}, user_id="u1")
    audit.log_command("s1", "ls", result="ok")
    audit.log_command("s2", "rm -rf /", result="blocked", blocked=True)
    audit.log_api_call("s1", "/v1/x", 200, 12.0)
    audit.log_api_call("s2", "/v1/y", 500, 34.0)
    audit.log_permission("s1", "write", True, reason="ok")
    audit.log_permission("s1", "write", False, reason="no")

    assert len(audit._entries) == 8

    critical = audit.get_entries(severity="critical")
    assert {e.action for e in critical} == {"file:delete", "command:execute"}
    assert all(e.severity == "critical" for e in critical)

    s1_entries = audit.get_entries(session_id="s1")
    assert all(e.session_id == "s1" for e in s1_entries)

    limited = audit.get_entries(limit=3)
    assert len(limited) == 3

    recent = audit.get_recent_critical(limit=1)
    assert len(recent) == 1

    # severities recorded
    severities = {(e.action, e.severity) for e in audit._entries}
    assert ("file:read", "info") in severities
    assert ("command:execute", "warning") in severities
    assert ("api:call", "info") in severities
    assert ("api:call", "warning") in severities
    assert ("permission:write", "warning") in severities
    assert ("permission:write", "info") in severities


async def test_audit_spawn_persist_task_tracking() -> None:
    audit = AuditSystem()
    ran: list[bool] = []

    async def work() -> None:
        ran.append(True)

    audit._spawn_persist(work())
    for _ in range(5):
        await asyncio.sleep(0)
    assert ran == [True]
    assert audit._persist_tasks == set()


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.commits = 0

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, *exc: Any) -> bool:
        return False

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1


async def test_audit_persist_success(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.storage as storage

    fake = _FakeSession()
    monkeypatch.setattr(storage, "async_session", lambda: fake)

    audit = AuditSystem()
    await audit._persist(
        session_id="s1",
        action="file:read",
        severity="info",
        details={"path": "/a"},
        result="r",
        user_id="u1",
    )
    assert fake.commits == 1
    assert len(fake.added) == 1
    assert fake.added[0].action == "file:read"


async def test_audit_persist_failure_is_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.storage as storage

    def boom() -> Any:
        raise RuntimeError("db down")

    monkeypatch.setattr(storage, "async_session", boom)
    audit = AuditSystem()
    # must not raise
    await audit._persist(
        session_id="s1",
        action="file:read",
        severity="info",
        details={},
    )
