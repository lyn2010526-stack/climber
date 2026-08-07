"""Tests for app.core.security_sandbox module."""

from __future__ import annotations

from unittest import mock

import pytest

from app.core.security_sandbox import (
    AgentMode,
    ApprovalStatus,
    AuditEntry,
    AuditSystem,
    CodeSandbox,
    ExecutionMode,
    PermissionApprovalSystem,
    PermissionLevel,
    PermissionRequest,
    PermissionRule,
    SandboxConfig,
    SecuritySandbox,
    validate_command_allowlist,
    validate_tool_input,
)


class TestPermissionRule:
    """Tests for PermissionRule."""

    def test_create_rule(self):
        rule = PermissionRule(action="read", resource_pattern="*.py", level=PermissionLevel.ALLOW)
        assert rule.action == "read"
        assert rule.resource_pattern == "*.py"
        assert rule.level == PermissionLevel.ALLOW


class TestValidateToolInput:
    """Tests for validate_tool_input function."""

    def test_valid_input(self):
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "count": {"type": "integer"}},
            "required": ["name"],
        }
        validate_tool_input(schema, {"name": "test"})

    def test_missing_required(self):
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        with pytest.raises(Exception):
            validate_tool_input(schema, {})

    def test_wrong_type(self):
        schema = {
            "type": "object",
            "properties": {"count": {"type": "integer"}},
        }
        with pytest.raises(Exception):
            validate_tool_input(schema, {"count": "not_a_number"})


class TestSandboxConfig:
    """Tests for SandboxConfig."""

    def test_default_config(self):
        config = SandboxConfig(workdir="/tmp/test")
        assert config.workdir == "/tmp/test"
        assert isinstance(config.allowed_paths, list)
        assert isinstance(config.blocked_paths, list)
        assert config.max_file_size_mb == 50
        assert config.max_output_size_kb == 500
        assert config.command_timeout_seconds == 120
        assert config.enable_network is False

    def test_custom_config(self):
        config = SandboxConfig(
            workdir="/workspace",
            allowed_paths=["/tmp"],
            max_file_size_mb=100,
            enable_network=True,
        )
        assert config.workdir == "/workspace"
        assert "/tmp" in config.allowed_paths
        assert config.max_file_size_mb == 100
        assert config.enable_network is True


class TestSecuritySandbox:
    """Tests for SecuritySandbox."""

    def test_create_sandbox(self):
        sandbox = SecuritySandbox()
        assert sandbox is not None

    def test_validate_file_access(self):
        sandbox = SecuritySandbox()
        result = sandbox.validate_file_access("/workspace/test.py")
        assert isinstance(result, tuple)

    def test_validate_command(self):
        sandbox = SecuritySandbox()
        result = sandbox.validate_command("ls -la")
        assert isinstance(result, tuple)

    def test_sanitize_output(self):
        sandbox = SecuritySandbox()
        result = sandbox.sanitize_output("test output")
        assert isinstance(result, str)


class TestValidateCommandAllowlist:
    """Tests for validate_command_allowlist."""

    def test_safe_command(self):
        ok, reason = validate_command_allowlist("ls -la")
        assert isinstance(ok, bool)

    def test_dangerous_command(self):
        ok, reason = validate_command_allowlist("rm -rf /")
        assert isinstance(ok, bool)


class TestCodeSandbox:
    """Tests for CodeSandbox."""

    def test_create_code_sandbox(self):
        sandbox = CodeSandbox()
        assert sandbox is not None


class TestPermissionApprovalSystem:
    """Tests for PermissionApprovalSystem."""

    def test_create_system(self):
        system = PermissionApprovalSystem()
        assert system is not None

    def test_request_permission(self):
        system = PermissionApprovalSystem()
        request = system.request_permission("session-1", "write", "Write to file")
        assert request is not None
        assert request.action == "write"
        assert request.details == "Write to file"

    def test_grant_permission(self):
        system = PermissionApprovalSystem()
        request = system.request_permission("session-1", "write", "Write to file")
        result = system.grant_permission(request.id)
        assert result is not None

    def test_deny_permission(self):
        system = PermissionApprovalSystem()
        request = system.request_permission("session-1", "write", "Write to file")
        result = system.deny_permission(request.id)
        assert result is not None

    def test_grant_nonexistent(self):
        system = PermissionApprovalSystem()
        result = system.grant_permission("nonexistent")
        assert result is None

    def test_deny_nonexistent(self):
        system = PermissionApprovalSystem()
        result = system.deny_permission("nonexistent")
        assert result is None


class TestAuditSystem:
    """Tests for AuditSystem."""

    def test_create_audit(self):
        audit = AuditSystem()
        assert audit is not None

    def test_log_file_operation(self):
        audit = AuditSystem()
        with mock.patch("asyncio.create_task"):
            audit.log_file_operation("session-1", "write", "/tmp/test.txt")
        assert len(audit._entries) > 0

    def test_log_command(self):
        audit = AuditSystem()
        with mock.patch("asyncio.create_task"):
            audit.log_command("session-1", "ls -la")
        assert len(audit._entries) > 0

    def test_log_api_call(self):
        audit = AuditSystem()
        with mock.patch("asyncio.create_task"):
            audit.log_api_call("session-1", "/api/test", 200, 500.0)
        assert len(audit._entries) > 0

    def test_get_recent_critical(self):
        audit = AuditSystem()
        with mock.patch("asyncio.create_task"):
            audit.log_file_operation("session-1", "delete", "/tmp/test.txt")
        entries = audit.get_recent_critical()
        assert isinstance(entries, list)
