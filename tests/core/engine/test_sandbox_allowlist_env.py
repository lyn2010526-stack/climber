"""Operator control over the now load-bearing command allowlist.

``SandboxConfig.allowed_commands`` became enforced (see
``tests/core/engine/test_sandbox_allowed_commands.py``), and
``app/main.py`` builds ``SandboxConfig()`` with no arguments. Without an
environment hook the new gate could not be widened without a code change, so
``CLIMBER_SANDBOX_ALLOWED_COMMANDS`` adds to the default list.

These tests pin that the hook is additive, tolerant of whitespace, cannot empty
the list, and leaves the shipped default untouched when unset.
"""

from __future__ import annotations

import importlib

import pytest

from app.core import sandbox as sandbox_module
from app.core.sandbox import SandboxConfig


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(sandbox_module._ALLOWED_COMMANDS_ENV, raising=False)


def test_default_allowlist_unchanged_when_env_unset() -> None:
    config = SandboxConfig()
    assert config.allowed_commands == list(sandbox_module._DEFAULT_ALLOWED_COMMANDS)
    for expected in ("python3", "ls", "grep"):
        assert expected in config.allowed_commands


def test_env_adds_new_executables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(sandbox_module._ALLOWED_COMMANDS_ENV, "git,go,pytest")
    config = SandboxConfig()
    assert "git" in config.allowed_commands
    assert "go" in config.allowed_commands
    assert "pytest" in config.allowed_commands
    # additive: the defaults are still there
    assert "python3" in config.allowed_commands
    assert "ls" in config.allowed_commands


def test_env_tolerates_whitespace_and_empty_segments(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(sandbox_module._ALLOWED_COMMANDS_ENV, " git , , go ,, ")
    config = SandboxConfig()
    assert "git" in config.allowed_commands
    assert "go" in config.allowed_commands
    assert "" not in config.allowed_commands


def test_env_accepts_absolute_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(sandbox_module._ALLOWED_COMMANDS_ENV, "/usr/bin/git, /opt/tools/rg")
    config = SandboxConfig()
    assert "git" in config.allowed_commands
    assert "rg" in config.allowed_commands
    assert "/usr/bin/git" not in config.allowed_commands


def test_env_cannot_empty_the_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    """A whitespace-only or delimiter-only value must not disable everything."""
    monkeypatch.setenv(sandbox_module._ALLOWED_COMMANDS_ENV, " , , ")
    assert SandboxConfig().allowed_commands == list(sandbox_module._DEFAULT_ALLOWED_COMMANDS)


def test_env_does_not_duplicate_existing_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(sandbox_module._ALLOWED_COMMANDS_ENV, "ls,grep,ls")
    allowed = SandboxConfig().allowed_commands
    assert allowed.count("ls") == 1
    assert allowed.count("grep") == 1
    # order of the defaults is preserved
    assert allowed[: len(sandbox_module._DEFAULT_ALLOWED_COMMANDS)] == list(
        sandbox_module._DEFAULT_ALLOWED_COMMANDS
    )


def test_added_executable_actually_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end: an env-added executable is accepted by the enforcement gate."""
    monkeypatch.setenv(sandbox_module._ALLOWED_COMMANDS_ENV, "echo")
    executor = sandbox_module.SandboxExecutor(SandboxConfig(workdir="."))
    allowed, reason = executor._is_command_safe("echo round-trip", ".")
    assert allowed is True, reason


def test_default_still_blocks_non_allowlisted(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no env set, a command outside the default list stays refused."""
    executor = sandbox_module.SandboxExecutor(SandboxConfig(workdir="."))
    allowed, reason = executor._is_command_safe("curl http://example.com", ".")
    assert allowed is False
    assert "allowed_commands" in reason


def test_resolver_is_recomputed_per_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reading the env at construction time keeps tests independent of order."""
    monkeypatch.setenv(sandbox_module._ALLOWED_COMMANDS_ENV, "one")
    first = sandbox_module._resolve_allowed_commands()
    monkeypatch.setenv(sandbox_module._ALLOWED_COMMANDS_ENV, "two")
    second = sandbox_module._resolve_allowed_commands()
    assert "one" in first and "one" not in second
    assert "two" in second and "two" not in first


def test_module_reload_keeps_default_constant() -> None:
    """Reloading must not lose the shipped defaults (regression guard)."""
    module = importlib.reload(sandbox_module)
    assert "python3" in module._DEFAULT_ALLOWED_COMMANDS
    assert "git" not in module._DEFAULT_ALLOWED_COMMANDS
