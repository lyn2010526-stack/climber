"""Tests for security sandbox integration with agent engine."""

import os

import pytest

os.environ.setdefault("APP_TESTING", "true")

from app.core.security_sandbox import SandboxConfig, SecuritySandbox  # noqa: E402


@pytest.fixture
def sandbox(tmp_path):
    return SecuritySandbox(SandboxConfig(workdir=str(tmp_path)))


def test_validate_command_blocks_hazard(sandbox):
    bad = "rm -rf /etc"
    ok, reason = sandbox.validate_command(bad)
    assert ok is False
    assert "hazard" in reason.lower() or "blocked" in reason.lower()


def test_validate_command_allows_safe(sandbox):
    ok, _ = sandbox.validate_command("ls -la")
    assert ok is True


def test_validate_file_access_blocks_outside(sandbox, tmp_path):
    ok, reason = sandbox.validate_file_access("/etc/passwd", "read")
    assert ok is False
    assert "blocked" in reason.lower() or "outside" in reason.lower()


def test_validate_file_access_allows_within(sandbox, tmp_path):
    target = tmp_path / "hello.txt"
    target.write_text("hi")
    ok, _ = sandbox.validate_file_access(str(target), "read")
    assert ok is True


def test_sanitize_output_truncates(sandbox):
    big = "x" * (sandbox.config.max_output_size_kb * 1024 + 100)
    out = sandbox.sanitize_output(big)
    assert "truncated" in out.lower()


@pytest.mark.asyncio
async def test_executor_validator_rejects():
    from app.core.parallel import ParallelToolExecutor

    calls_made = []

    class FakeRegistry:
        async def execute(self, name, args):
            calls_made.append((name, args))
            return "should-not-run"

    def reject(name, args):
        if name == "run_command" and "rm -rf" in str(args.get("command", "")):
            return False, "match hazard pattern"
        return True, "OK"

    ex = ParallelToolExecutor(FakeRegistry(), validator=reject)
    res = await ex.execute_all([{
        "function": {"name": "run_command", "arguments": {"command": "rm -rf /etc"}},
    }])
    assert len(res) == 1
    assert res[0].success is False
    assert "blocked by sandbox" in res[0].error
    assert calls_made == [], "registry.execute must not be called for blocked tools"


@pytest.mark.asyncio
async def test_executor_validator_allows_safe():
    from app.core.parallel import ParallelToolExecutor

    class FakeRegistry:
        async def execute(self, name, args):
            return f"ran {name}"

    def ok(name, args):
        return True, "OK"

    ex = ParallelToolExecutor(FakeRegistry(), validator=ok)
    res = await ex.execute_all([{
        "function": {"name": "safe_tool", "arguments": {"x": 1}},
    }])
    assert res[0].success is True
    assert res[0].result == "ran safe_tool"
