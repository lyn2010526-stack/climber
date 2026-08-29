"""Security regression tests for filesystem isolation glob boundaries."""

from pathlib import Path

from app.core.security.fs_isolation import FSIsolationConfig, FSIsolationManager


def test_glob_blocked_directory_covers_descendants(tmp_path: Path):
    manager = FSIsolationManager(FSIsolationConfig(blocked_paths=[str(tmp_path / "*") + "/.ssh"]))

    allowed, reason = manager.validate_path(str(tmp_path / "alice/.ssh/id_rsa"))

    assert not allowed
    assert "blocked" in reason


def test_glob_blocked_directory_does_not_match_sibling_prefix(tmp_path: Path):
    manager = FSIsolationManager(FSIsolationConfig(blocked_paths=[str(tmp_path / "*") + "/.ssh"]))

    allowed, _reason = manager.validate_path(str(tmp_path / "alice/.ssh-notes"))

    assert allowed
