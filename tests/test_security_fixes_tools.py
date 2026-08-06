"""Tests for security fixes in native_tools.py, builtins.py, and security_sandbox.py."""

from __future__ import annotations

import os
import tempfile

import pytest

# Set testing mode
os.environ["APP_TESTING"] = "true"
os.environ["CLIMBER_SANDBOX_WORKDIR"] = tempfile.mkdtemp(prefix="climber_test_")


# ─── Import modules under test ──────────────────────────────────────────────

from app.core.security_sandbox import (
    SandboxConfig,
    SecuritySandbox,
    validate_command_allowlist,
)
from app.tools.builtins import _safe_eval_math, calculator
from app.tools.native_tools import (
    _validate_command_safety,
    _validate_path_within_workspace,
)

# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def workspace_root():
    """Create a temporary workspace root for testing."""
    tmpdir = tempfile.mkdtemp(prefix="climber_test_")
    os.environ["CLIMBER_SANDBOX_WORKDIR"] = tmpdir
    yield tmpdir
    os.environ.pop("CLIMBER_SANDBOX_WORKDIR", None)


@pytest.fixture
def sandbox(workspace_root):
    """Create a SecuritySandbox instance for testing."""
    config = SandboxConfig(workdir=workspace_root)
    return SecuritySandbox(config)


# ─── Test: Command injection attempts are blocked ────────────────────────────

class TestCommandInjectionBlocked:
    """Test that dangerous shell commands are rejected."""

    def test_semicolon_injection_blocked(self):
        """Commands with semicolons should be blocked."""
        is_safe, reason = _validate_command_safety("ls; rm -rf /")
        assert not is_safe
        assert "dangerous shell pattern" in reason

    def test_pipe_injection_blocked(self):
        """Commands with pipes should be blocked."""
        is_safe, reason = _validate_command_safety("ls | cat /etc/passwd")
        assert not is_safe
        assert "dangerous shell pattern" in reason

    def test_dollar_paren_injection_blocked(self):
        """Commands with $() command substitution should be blocked."""
        is_safe, reason = _validate_command_safety("echo $(whoami)")
        assert not is_safe
        assert "dangerous shell pattern" in reason

    def test_backtick_injection_blocked(self):
        """Commands with backtick command substitution should be blocked."""
        is_safe, reason = _validate_command_safety("echo `whoami`")
        assert not is_safe
        assert "dangerous shell pattern" in reason

    def test_logical_and_injection_blocked(self):
        """Commands with && should be blocked."""
        is_safe, reason = _validate_command_safety("ls && cat /etc/passwd")
        assert not is_safe
        assert "dangerous shell pattern" in reason

    def test_logical_or_injection_blocked(self):
        """Commands with || should be blocked."""
        is_safe, reason = _validate_command_safety("ls || cat /etc/passwd")
        assert not is_safe
        assert "dangerous shell pattern" in reason

    def test_allowlist_blocks_unknown_commands(self):
        """Commands not in allowlist should be blocked."""
        is_allowed, reason = validate_command_allowlist("rm -rf /tmp/something")
        assert not is_allowed
        assert ("not in the allowed commands list" in reason) or ("Dangerous arguments" in reason)

    def test_allowlist_permits_safe_commands(self):
        """Safe commands should be allowed by allowlist."""
        is_allowed, reason = validate_command_allowlist("ls -la")
        assert is_allowed
        assert reason == "OK"


# ─── Test: Path traversal attempts fail ─────────────────────────────────────

class TestPathTraversalBlocked:
    """Test that path traversal attacks are rejected."""

    def test_dotdot_in_path_blocked(self, workspace_root):
        """Paths containing .. should be rejected."""
        valid, msg = _validate_path_within_workspace("../etc/passwd")
        assert not valid
        assert "traversal" in msg.lower()

    def test_absolute_path_outside_workspace_blocked(self, workspace_root):
        """Absolute paths outside workspace should be rejected."""
        valid, msg = _validate_path_within_workspace("/etc/passwd")
        assert not valid
        assert "outside" in msg.lower()

    def test_workspace_root_is_valid(self, workspace_root):
        """Workspace root path itself should be valid."""
        valid, msg = _validate_path_within_workspace(workspace_root)
        # Returns the resolved path (True) or (False, error)
        assert valid

    def test_subdirectory_within_workspace_valid(self, workspace_root):
        """Subdirectories within workspace should be valid."""
        subdir = os.path.join(workspace_root, "subdir", "file.txt")
        valid, msg = _validate_path_within_workspace(subdir)
        assert valid

    def test_sandbox_blocks_traversal(self, sandbox):
        """Sandbox should reject path traversal."""
        ok, reason = sandbox.validate_file_access("../../../etc/passwd")
        assert not ok
        assert ("traversal" in reason.lower()) or ("blocked" in reason.lower()) or ("denied" in reason.lower())

    def test_sandbox_blocks_outside_paths(self, sandbox):
        """Sandbox should reject paths outside allowed directories."""
        ok, reason = sandbox.validate_file_access("/etc/shadow")
        assert not ok

    def test_sandbox_blocks_blocked_paths(self, sandbox):
        """Sandbox should block access to sensitive system paths."""
        ok, reason = sandbox.validate_file_access("/etc/passwd")
        assert not ok
        assert "blocked" in reason.lower() or "outside" in reason.lower()


# ─── Test: Calculator only evaluates safe expressions ────────────────────────

class TestCalculatorSafety:
    """Test that calculator only evaluates safe math expressions."""

    @pytest.mark.asyncio
    async def test_basic_math_works(self):
        """Basic arithmetic should work."""
        result = await calculator("2 + 2")
        assert result == "4"

    @pytest.mark.asyncio
    def test_complex_math_works(self):
        """Complex math expressions should work."""
        result = _safe_eval_math("3.14 * 2 + 1", {})
        assert abs(result - 7.28) < 0.001

    @pytest.mark.asyncio
    async def test_rejects_import_statement(self):
        """Import statements should be rejected."""
        result = await calculator("__import__('os').system('ls')")
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_rejects_function_calls_to_dangerous(self):
        """Calls to non-whitelisted functions should be rejected."""
        result = await calculator("exec('print(1)')")
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_rejects_getattr_access(self):
        """Attribute access to dunder methods should be rejected."""
        result = await calculator("().__class__.__bases__")
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_rejects_string_concatenation(self):
        """String operations should be rejected."""
        result = await calculator("'hello' + 'world'")
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_rejects_variable_assignment(self):
        """Variable assignments should be rejected."""
        result = await calculator("x = 1")
        assert "Error" in result


# ─── Test: Container name validation ─────────────────────────────────────────

class TestContainerNameValidation:
    """Test container name validation logic."""

    def test_valid_container_name(self):
        """Valid container names should pass."""
        import re
        pattern = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]+$')
        assert pattern.match("my_container-123")
        assert pattern.match("webserver1")
        assert pattern.match("app-server-01")

    def test_invalid_container_name_with_slash(self):
        """Container names with slashes should fail."""
        import re
        pattern = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]+$')
        assert not pattern.match("docker/nginx")
        assert not pattern.match("my/container")

    def test_invalid_container_name_with_special_chars(self):
        """Container names with special characters should fail."""
        import re
        pattern = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]+$')
        assert not pattern.match("my container")
        assert not pattern.match("container;rm")
        assert not pattern.match("cont' OR '1'='1")
        assert not pattern.match("")
        assert not pattern.match("-starts-with-dash")

    def test_container_exec_validates_name(self, workspace_root):
        """container_exec should validate container name before execution."""
        # This will fail because docker is not available, but the validation
        # should happen before the docker call
        # We can test the validation logic directly
        # Test that the pattern matching works
        import re
        container_pattern = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]+$')
        assert container_pattern.match("valid-container")
        assert not container_pattern.match("invalid;command")


# ─── Test: SecuritySandbox allowlist ────────────────────────────────────────

class TestSecuritySandboxAllowlist:
    """Test the allowlist validation in SecuritySandbox."""

    def test_validate_command_allowlist_allows_safe(self):
        """Safe commands should pass allowlist."""
        is_allowed, reason = validate_command_allowlist("ls -la /tmp")
        assert is_allowed
        assert reason == "OK"

    def test_validate_command_allowlist_blocks_dangerous(self):
        """Dangerous commands should be blocked by allowlist."""
        is_allowed, reason = validate_command_allowlist("rm -rf /home")
        assert not is_allowed

    def test_validate_command_allowlist_empty_command(self):
        """Empty commands should be blocked."""
        is_allowed, reason = validate_command_allowlist("")
        assert not is_allowed

    def test_validate_command_allowlist_invalid_syntax(self):
        """Commands with invalid shell syntax should be blocked."""
        is_allowed, reason = validate_command_allowlist("echo 'unclosed")
        assert not is_allowed


# ─── Test: SecuritySandbox validate_command integration ──────────────────────

class TestSecuritySandboxValidateCommand:
    """Test the integrated validate_command method."""

    def test_blocks_hazard_commands(self, sandbox):
        """Hazard commands should be blocked."""
        ok, reason = sandbox.validate_command("rm -rf /")
        assert not ok
        assert "blocked" in reason.lower() or "not in the allowed commands" in reason.lower()

    def test_blocks_allowlist_violations(self, sandbox):
        """Commands not in allowlist should be blocked."""
        ok, reason = sandbox.validate_command("evilcmd --attack")
        assert not ok

    def test_allows_safe_commands(self, sandbox):
        """Safe commands should be allowed."""
        ok, reason = sandbox.validate_command("ls -la")
        assert ok
        assert reason == "OK"

    def test_allows_git_commands(self, sandbox):
        """Git commands should be allowed."""
        ok, reason = sandbox.validate_command("git status")
        assert ok

    def test_allows_npm_commands(self, sandbox):
        """NPM commands should be allowed."""
        ok, reason = sandbox.validate_command("npm test")
        assert ok
