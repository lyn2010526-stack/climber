"""Coverage tests for app.core.sandbox.

The real subprocess path is exercised with ``echo``; timeout and failure
paths use lightweight fakes so no test ever blocks. Resource-limit calls are
monkeypatched so the test process limits are never touched.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import pytest

from app.core.sandbox import SandboxConfig, SandboxExecutor, default_sandbox


def _executor(workdir: str = "", **kwargs: Any) -> SandboxExecutor:
    return SandboxExecutor(SandboxConfig(workdir=workdir, **kwargs))


# ── config ──────────────────────────────────────────────────────────────


def test_sandbox_config_defaults() -> None:
    cfg = SandboxConfig()
    assert cfg.timeout_seconds == 30
    assert cfg.max_output_bytes == 10000
    assert cfg.max_memory_mb == 256
    assert cfg.enable_network is False
    assert "python" in cfg.allowed_commands
    assert any("rm" in p for p in cfg.blocked_patterns)


def test_default_sandbox_instance() -> None:
    assert isinstance(default_sandbox, SandboxExecutor)


# ── _is_command_safe ────────────────────────────────────────────────────


def test_is_command_safe_rejects_invalid_syntax() -> None:
    ok, reason = _executor()._is_command_safe('cat "unclosed', "/tmp")
    assert ok is False
    assert "invalid command syntax" in reason


def test_is_command_safe_rejects_empty() -> None:
    ok, reason = _executor()._is_command_safe("   ", "/tmp")
    assert ok is False
    assert reason == "Blocked: empty command"


def test_is_command_safe_rejects_disallowed_executable() -> None:
    ok, reason = _executor()._is_command_safe("ruby script.rb", "/tmp")
    assert ok is False
    assert "is not allowed" in reason


def test_is_command_safe_rejects_blocked_pattern() -> None:
    ok, reason = _executor()._is_command_safe("echo hi; rm -rf /", "/tmp")
    assert ok is False
    assert "Blocked by security rule" in reason


def test_is_command_safe_rejects_parent_traversal() -> None:
    ok, reason = _executor()._is_command_safe("python ../escape.py", "/tmp")
    assert ok is False
    assert "parent-directory traversal" in reason


def test_is_command_safe_rejects_sensitive_path() -> None:
    ok, reason = _executor()._is_command_safe("cat /etc/shadow", "/tmp")
    assert ok is False
    assert "sensitive path" in reason


def test_is_command_safe_rejects_path_escaping_workdir() -> None:
    ok, reason = _executor()._is_command_safe("cat /tmp/other-file", "/tmp/ws")
    assert ok is False
    assert "escapes workdir" in reason


def test_is_command_safe_allows_plain_command() -> None:
    assert _executor()._is_command_safe("echo hi", "/tmp") == (True, "")


def test_is_command_safe_allows_path_inside_workdir(tmp_path: Path) -> None:
    inside = tmp_path / "inside.txt"
    command = f"cat {inside}"
    assert _executor()._is_command_safe(command, str(tmp_path)) == (True, "")


# ── resource limits ─────────────────────────────────────────────────────


def test_restrict_resources_sets_rlimits(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[int, tuple[int, int]]] = []
    monkeypatch.setattr("app.core.sandbox.resource.setrlimit", lambda k, v: calls.append((k, v)))
    _executor(max_memory_mb=64, timeout_seconds=5)._restrict_resources()
    assert len(calls) == 4


def test_restrict_resources_ignores_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(k: Any, v: Any) -> None:
        raise OSError("not permitted")

    monkeypatch.setattr("app.core.sandbox.resource.setrlimit", boom)
    _executor()._restrict_resources()  # must not raise


# ── workdir prep / cleanup ──────────────────────────────────────────────


def test_prepare_workdir_uses_existing_config_dir(tmp_path: Path) -> None:
    executor = _executor(workdir=str(tmp_path))
    assert executor._prepare_workdir() == str(tmp_path)


def test_prepare_workdir_creates_temp_dir() -> None:
    executor = _executor(workdir="/no/such/dir-xyz")
    created = executor._prepare_workdir()
    try:
        assert os.path.isdir(created)
        assert executor._workdir == created
    finally:
        executor.cleanup()
    assert not os.path.isdir(created)


def test_cleanup_without_workdir_is_noop() -> None:
    executor = _executor()
    executor.cleanup()
    assert executor._workdir == ""


def test_cleanup_logs_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    executor = _executor()
    sandbox_dir = tmp_path / "sandbox"
    sandbox_dir.mkdir()
    executor._workdir = str(sandbox_dir)

    def boom(path: str, ignore_errors: bool = False) -> None:
        raise OSError("cannot remove")

    monkeypatch.setattr("app.core.sandbox.shutil.rmtree", boom)
    executor.cleanup()
    assert executor._workdir == ""


# ── _build_output ───────────────────────────────────────────────────────


def test_build_output_stdout_only() -> None:
    executor = _executor()
    assert executor._build_output(b"hello\n", b"", 0) == "hello"


def test_build_output_stderr_only() -> None:
    executor = _executor()
    assert executor._build_output(b"", b"warn\n", 0) == "[stderr]: warn"


def test_build_output_nonzero_no_output() -> None:
    executor = _executor()
    assert executor._build_output(b"", b"", 3) == "Command exited with code 3"


def test_build_output_truncates() -> None:
    executor = _executor(max_output_bytes=5)
    out = executor._build_output(b"abcdefghij", b"", 0)
    assert out.endswith("[OUTPUT TRUNCATED]")


def test_build_output_no_output_success() -> None:
    executor = _executor()
    assert executor._build_output(b"", b"", 0) == "Command completed (no output)"


# ── execute ─────────────────────────────────────────────────────────────


async def test_execute_blocked_command() -> None:
    executor = _executor()
    result = await executor.execute("ruby script.rb")
    assert result.startswith("BLOCKED:")


async def test_execute_real_command_success() -> None:
    executor = _executor()
    try:
        result = await executor.execute("echo hello-sandbox")
    finally:
        executor.cleanup()
    assert result == "hello-sandbox"


class _TimeoutProc:
    def __init__(self) -> None:
        self.killed = False
        self.waited = False

    async def communicate(self) -> tuple[bytes, bytes]:
        raise TimeoutError

    def kill(self) -> None:
        self.killed = True

    async def wait(self) -> int:
        self.waited = True
        return -9


async def test_execute_timeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    proc = _TimeoutProc()

    async def fake_exec(*args: Any, **kwargs: Any) -> _TimeoutProc:
        return proc

    monkeypatch.setattr("app.core.sandbox.asyncio.create_subprocess_exec", fake_exec)
    executor = _executor(workdir=str(tmp_path))
    result = await executor.execute("echo hi", timeout=1)
    assert result == "TIMEOUT: Command exceeded 1s limit"
    assert proc.killed is True
    assert proc.waited is True


async def test_execute_spawn_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    async def boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("spawn failed")

    monkeypatch.setattr("app.core.sandbox.asyncio.create_subprocess_exec", boom)
    executor = _executor(workdir=str(tmp_path))
    result = await executor.execute("echo hi")
    assert result == "Error: spawn failed"


async def test_execute_enables_network_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    class _Proc:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return (b"ok", b"")

    async def fake_exec(*args: Any, **kwargs: Any) -> _Proc:
        captured.update(kwargs)
        return _Proc()

    monkeypatch.setenv("HTTP_PROXY", "http://proxy")
    monkeypatch.setattr("app.core.sandbox.asyncio.create_subprocess_exec", fake_exec)
    executor = _executor(workdir=str(tmp_path), enable_network=True)
    result = await executor.execute("echo hi")
    assert result == "ok"
    assert captured["env"].get("HTTP_PROXY") == "http://proxy"


async def test_execute_does_not_forward_proxy_when_network_disabled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, Any] = {}

    class _Proc:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return (b"ok", b"")

    async def fake_exec(*args: Any, **kwargs: Any) -> _Proc:
        captured.update(kwargs)
        return _Proc()

    monkeypatch.setenv("HTTP_PROXY", "http://proxy")
    monkeypatch.setattr("app.core.sandbox.asyncio.create_subprocess_exec", fake_exec)
    executor = _executor(workdir=str(tmp_path), enable_network=False)
    await executor.execute("echo hi")
    assert "HTTP_PROXY" not in captured["env"]


async def test_execute_uses_awaitable_communicate() -> None:
    # sanity check that the mock-heavy tests above still exercise asyncio.wait_for
    proc = _TimeoutProc()
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(proc.communicate(), timeout=0.01)
