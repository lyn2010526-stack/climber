from __future__ import annotations

from app.core.security_sandbox import SandboxConfig, SecuritySandbox


def test_file_access_requires_directory_boundary(tmp_path) -> None:
    sandbox = SecuritySandbox(SandboxConfig(workdir=str(tmp_path)))

    allowed, _ = sandbox.validate_file_access(str(tmp_path / "src" / "main.py"))
    escaped, _ = sandbox.validate_file_access(f"{tmp_path}-sibling/secret.txt")

    assert allowed is True
    assert escaped is False


def test_blocked_home_ssh_glob_matches_nested_files(tmp_path) -> None:
    sandbox = SecuritySandbox(
        SandboxConfig(workdir=str(tmp_path), blocked_paths=["/home/*/.ssh"])
    )

    allowed, reason = sandbox.validate_file_access("/home/demo/.ssh/id_ed25519")

    assert allowed is False
    assert "blocked list" in reason
