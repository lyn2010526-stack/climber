"""Round 4 security baseline: 10 focused and 5 integration scenarios."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.api.v1 import permissions as permissions_api
from app.core.permission_rules import (
    PermissionConfig,
    PermissionMode,
    PermissionRule,
    RuleDecision,
)
from app.core.security_sandbox import SandboxConfig, SecuritySandbox


def _sandbox(workdir: Path, **kwargs) -> SecuritySandbox:
    return SecuritySandbox(SandboxConfig(workdir=str(workdir), **kwargs))


# Focused scenarios 1-10
def test_s01_workspace_root_is_allowed(tmp_path):
    allowed, _ = _sandbox(tmp_path).validate_file_access(str(tmp_path))
    assert allowed


def test_s02_workspace_descendant_is_allowed(tmp_path):
    target = tmp_path / "nested" / "file.txt"
    allowed, _ = _sandbox(tmp_path).validate_file_access(str(target), "write")
    assert allowed


def test_s03_sibling_prefix_path_is_denied(tmp_path):
    workspace = tmp_path / "project"
    sibling = tmp_path / "project-secrets" / "token.txt"
    workspace.mkdir()
    sibling.parent.mkdir()

    allowed, _ = _sandbox(workspace).validate_file_access(str(sibling))
    assert not allowed


def test_s04_symlink_escape_is_denied(tmp_path):
    workspace = tmp_path / "project"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    link = workspace / "linked-outside"
    link.symlink_to(outside, target_is_directory=True)

    allowed, _ = _sandbox(workspace).validate_file_access(str(link / "secret.txt"))
    assert not allowed


def test_s05_additional_allowed_root_is_allowed(tmp_path):
    workspace = tmp_path / "project"
    shared = tmp_path / "shared"
    workspace.mkdir()
    shared.mkdir()

    allowed, _ = _sandbox(workspace, allowed_paths=[str(shared)]).validate_file_access(
        str(shared / "data.txt")
    )
    assert allowed


def test_s06_blocked_descendant_is_denied(tmp_path):
    workspace = tmp_path / "project"
    blocked = workspace / "private"
    blocked.mkdir(parents=True)

    allowed, _ = _sandbox(workspace, blocked_paths=[str(blocked)]).validate_file_access(
        str(blocked / "key.txt")
    )
    assert not allowed


def test_s07_blocked_sibling_prefix_does_not_overmatch(tmp_path):
    workspace = tmp_path / "project"
    blocked = workspace / "private"
    safe = workspace / "private-notes" / "readme.txt"
    safe.parent.mkdir(parents=True)

    allowed, _ = _sandbox(workspace, blocked_paths=[str(blocked)]).validate_file_access(str(safe))
    assert allowed


def test_s08_auto_mode_honors_explicit_deny_rule():
    config = PermissionConfig(
        mode=PermissionMode.AUTO,
        rules=[PermissionRule(decision=RuleDecision.DENY, tool="write_file")],
    )
    assert config.evaluate("write_file", {"path": "safe.txt"}) is RuleDecision.DENY


def test_s09_auto_mode_honors_denied_tools():
    config = PermissionConfig(mode=PermissionMode.AUTO, denied_tools=["external_*"])
    assert config.evaluate("external_publish", {}) is RuleDecision.DENY


def test_s10_permission_api_schema_accepts_safe_modes():
    for mode in (
        PermissionMode.DEFAULT,
        PermissionMode.PLAN,
        PermissionMode.ACCEPT_EDITS,
        PermissionMode.AUTO,
    ):
        parsed = permissions_api.PermissionConfigUpdate.model_validate({"mode": mode.value})
        assert parsed.mode == mode


# Integration scenarios 11-15
def test_e11_permission_api_schema_rejects_bypass():
    with pytest.raises(ValidationError):
        permissions_api.PermissionConfigUpdate(mode=PermissionMode.BYPASS)


@pytest.mark.asyncio
async def test_e12_permission_api_updates_safe_mode(monkeypatch):
    engine = SimpleNamespace(
        get_permission_config=lambda: PermissionConfig(),
        update_permission_config=lambda config: setattr(engine, "updated", config),
    )
    monkeypatch.setattr(permissions_api, "get_engine", lambda: engine)

    result = await permissions_api.update_permission_config(
        permissions_api.PermissionConfigUpdate(mode=PermissionMode.PLAN)
    )

    assert result == {"status": "updated", "mode": "plan"}
    assert engine.updated.mode is PermissionMode.PLAN


@pytest.mark.asyncio
async def test_e13_permission_api_preserves_explicit_deny(monkeypatch):
    engine = SimpleNamespace(
        get_permission_config=lambda: PermissionConfig(),
        update_permission_config=lambda config: setattr(engine, "updated", config),
    )
    monkeypatch.setattr(permissions_api, "get_engine", lambda: engine)
    update = permissions_api.PermissionConfigUpdate(
        mode=PermissionMode.AUTO,
        rules=[permissions_api.PermissionRuleSchema(decision="deny", tool="write_file")],
    )

    await permissions_api.update_permission_config(update)

    assert engine.updated.evaluate("write_file", {"path": "safe.txt"}) is RuleDecision.DENY


@pytest.mark.asyncio
async def test_e14_sandbox_validator_blocks_prefix_escape_before_execution(tmp_path):
    from app.core.parallel import ParallelToolExecutor

    calls = []
    workspace = tmp_path / "project"
    sibling = tmp_path / "project-secrets"
    workspace.mkdir()
    sibling.mkdir()
    sandbox = _sandbox(workspace)

    class Registry:
        async def execute(self, name, arguments):
            calls.append((name, arguments))
            return "executed"

    def validator(_name, arguments):
        return sandbox.validate_file_access(arguments["path"], "write")

    results = await ParallelToolExecutor(Registry(), validator=validator).execute_all(
        [{"id": "call-1", "function": {"name": "write_file", "arguments": {"path": str(sibling / "key")}}}]
    )

    assert not results[0].success
    assert calls == []


@pytest.mark.asyncio
async def test_e15_sandbox_validator_blocks_symlink_escape_before_execution(tmp_path):
    from app.core.parallel import ParallelToolExecutor

    calls = []
    workspace = tmp_path / "project"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    link = workspace / "external"
    link.symlink_to(outside, target_is_directory=True)
    sandbox = _sandbox(workspace)

    class Registry:
        async def execute(self, name, arguments):
            calls.append((name, arguments))
            return "executed"

    def validator(_name, arguments):
        return sandbox.validate_file_access(arguments["path"], "write")

    results = await ParallelToolExecutor(Registry(), validator=validator).execute_all(
        [{"id": "call-2", "function": {"name": "write_file", "arguments": {"path": str(link / "key")}}}]
    )

    assert not results[0].success
    assert calls == []


def test_a16_dangling_symlink_escape_is_denied(tmp_path):
    workspace = tmp_path / "project"
    outside = tmp_path / "outside"
    workspace.mkdir()
    link = workspace / "external"
    link.symlink_to(outside / "missing", target_is_directory=True)

    allowed, _ = _sandbox(workspace).validate_file_access(str(link / "new.txt"), "write")
    assert not allowed


def test_a17_blocked_glob_matches_directory_descendants(tmp_path):
    workspace = tmp_path / "home"
    ssh_file = workspace / "alice" / ".ssh" / "id_ed25519"
    notes = workspace / "alice" / ".ssh-notes" / "readme.txt"
    ssh_file.parent.mkdir(parents=True)
    notes.parent.mkdir(parents=True)
    sandbox = _sandbox(workspace, blocked_paths=[str(workspace / "*" / ".ssh")])

    assert not sandbox.validate_file_access(str(ssh_file))[0]
    assert sandbox.validate_file_access(str(notes))[0]


@pytest.mark.parametrize("mode", [1, True, {}, "unknown", "bypass"])
def test_a18_permission_schema_rejects_invalid_modes(mode):
    with pytest.raises(ValidationError):
        permissions_api.PermissionConfigUpdate.model_validate({"mode": mode})
