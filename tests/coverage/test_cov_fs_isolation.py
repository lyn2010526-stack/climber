"""Coverage tests for app.core.security.fs_isolation."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.core.security.fs_isolation import FSIsolationConfig, FSIsolationManager


def _manager(**kwargs: object) -> FSIsolationManager:
    return FSIsolationManager(FSIsolationConfig(**kwargs))  # type: ignore[arg-type]


# ── config ──────────────────────────────────────────────────────────────


def test_default_config_values() -> None:
    cfg = FSIsolationConfig()
    assert cfg.allowed_paths == []
    assert "/etc/shadow" in cfg.blocked_paths
    assert ".py" in cfg.allowed_extensions
    assert cfg.temp_dir == ""
    assert cfg.max_file_size_mb == 50


def test_set_config_merges_blocked_paths_with_defaults() -> None:
    manager = FSIsolationManager()
    custom = FSIsolationConfig(
        allowed_paths=["/srv/app"],
        blocked_paths=["/srv/app/secret"],
        read_only_paths=["/srv/app/ro"],
        temp_dir="/tmp/x",
        max_file_size_mb=5,
        allowed_extensions=[".py"],
    )
    manager.set_config(custom)
    # built-in defaults are preserved even though custom did not list them
    assert "/etc/shadow" in manager.config.blocked_paths
    assert "/srv/app/secret" in manager.config.blocked_paths
    assert manager.config.allowed_paths == ["/srv/app"]
    assert manager.config.max_file_size_mb == 5


def test_set_config_ignores_empty_custom_blocked_entries() -> None:
    manager = FSIsolationManager()
    manager.set_config(FSIsolationConfig(blocked_paths=["", "/custom/block"]))
    assert "" not in manager.config.blocked_paths
    assert "/custom/block" in manager.config.blocked_paths


# ── validate_path ───────────────────────────────────────────────────────


def test_validate_path_empty() -> None:
    ok, reason = FSIsolationManager().validate_path("")
    assert ok is False
    assert reason == "Empty path"


def test_validate_path_invalid_embedded_null() -> None:
    ok, reason = FSIsolationManager().validate_path("/tmp/\0bad")
    assert ok is False
    assert reason.startswith("Invalid path:")


def test_validate_path_blocked_default() -> None:
    ok, reason = FSIsolationManager().validate_path("/etc/passwd")
    assert ok is False
    assert reason.startswith("Path is blocked:")


def test_validate_path_outside_allowed() -> None:
    manager = _manager(allowed_paths=["/srv/app"])
    ok, reason = manager.validate_path("/tmp/other")
    assert ok is False
    assert reason.startswith("Path outside allowed directories:")


def test_validate_path_inside_allowed(tmp_path: Path) -> None:
    manager = _manager(allowed_paths=[str(tmp_path)])
    ok, reason = manager.validate_path(str(tmp_path / "file.py"))
    assert ok is True
    assert reason == ""


def test_validate_path_allowed_list_with_invalid_entry() -> None:
    # an allowed path that cannot be resolved is skipped, leaving path rejected
    manager = _manager(allowed_paths=["/tmp/\0bad"])
    ok, _ = manager.validate_path("/tmp/somewhere")
    assert ok is False


# ── sanitize_path ───────────────────────────────────────────────────────


def test_sanitize_path_empty_raises() -> None:
    with pytest.raises(ValueError, match="Empty path"):
        FSIsolationManager().sanitize_path("")


def test_sanitize_path_traversal_raises() -> None:
    with pytest.raises(ValueError, match="Path traversal detected"):
        FSIsolationManager().sanitize_path("foo/../bar")


def test_sanitize_path_normal(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b.txt"
    assert FSIsolationManager().sanitize_path(str(target)) == str(target.resolve())


# ── symlink resolution (private helper) ─────────────────────────────────


def test_safe_resolve_symlink_relative_target(tmp_path: Path) -> None:
    real = tmp_path / "real.txt"
    real.write_text("x", encoding="utf-8")
    link = tmp_path / "link.txt"
    os.symlink("real.txt", link)
    resolved = FSIsolationManager()._safe_resolve_symlink(link)
    assert resolved == real.resolve()


def test_safe_resolve_symlink_blocked_target(tmp_path: Path) -> None:
    link = tmp_path / "evil"
    os.symlink("/etc/passwd", link)
    with pytest.raises(ValueError, match="Symlink target is blocked"):
        FSIsolationManager()._safe_resolve_symlink(link)


def test_safe_resolve_symlink_non_symlink(tmp_path: Path) -> None:
    plain = tmp_path / "plain.txt"
    plain.write_text("x", encoding="utf-8")
    assert FSIsolationManager()._safe_resolve_symlink(plain) == plain


# ── temp dirs ───────────────────────────────────────────────────────────


def test_create_temp_default_root() -> None:
    manager = FSIsolationManager()
    tmp = manager.create_temp()
    try:
        assert os.path.isdir(tmp)
        assert tmp in manager._temp_dirs
    finally:
        manager.cleanup_temp()


def test_create_temp_in_configured_dir(tmp_path: Path) -> None:
    manager = _manager(temp_dir=str(tmp_path))
    tmp = manager.create_temp(prefix="custom_")
    try:
        assert os.path.dirname(tmp) == str(tmp_path)
        assert os.path.basename(tmp).startswith("custom_")
    finally:
        manager.cleanup_temp()


def test_cleanup_temp_specific_path(tmp_path: Path) -> None:
    manager = _manager(temp_dir=str(tmp_path))
    tmp = manager.create_temp()
    assert os.path.isdir(tmp)
    manager.cleanup_temp(tmp)
    assert not os.path.isdir(tmp)
    assert tmp not in manager._temp_dirs


def test_cleanup_temp_specific_path_outside_registry(tmp_path: Path) -> None:
    manager = FSIsolationManager()
    stray = tmp_path / "stray"
    stray.mkdir()
    manager.cleanup_temp(str(stray))
    assert not stray.exists()


def test_cleanup_temp_specific_nonexistent_path() -> None:
    # path not in registry and not on disk -> nothing happens, no error
    FSIsolationManager().cleanup_temp("/no/such/dir_xyz")


def test_cleanup_temp_all_skips_already_removed() -> None:
    manager = FSIsolationManager()
    tmp = manager.create_temp()
    os.rmdir(tmp)
    manager.cleanup_temp()  # registry still references it but it is gone
    assert manager._temp_dirs == []


def test_cleanup_temp_all() -> None:
    manager = FSIsolationManager()
    a = manager.create_temp()
    b = manager.create_temp()
    manager.cleanup_temp()
    assert not os.path.isdir(a)
    assert not os.path.isdir(b)
    assert manager._temp_dirs == []


# ── read-only ───────────────────────────────────────────────────────────


def test_is_read_only_matches_and_prefix(tmp_path: Path) -> None:
    manager = _manager(read_only_paths=[str(tmp_path)])
    assert manager.is_read_only(str(tmp_path)) is True
    assert manager.is_read_only(str(tmp_path / "child.txt")) is True
    assert manager.is_read_only("/somewhere/else") is False


def test_is_read_only_invalid_path() -> None:
    assert FSIsolationManager().is_read_only("/tmp/\0bad") is False


# ── file type & size ────────────────────────────────────────────────────


def test_validate_file_type_allowlist() -> None:
    manager = FSIsolationManager()
    ok, _ = manager.validate_file_type("script.py")
    assert ok is True
    ok, reason = manager.validate_file_type("evil.exe")
    assert ok is False
    assert "not allowed" in reason


def test_validate_file_type_empty_allowlist_allows_all() -> None:
    manager = _manager(allowed_extensions=[])
    ok, reason = manager.validate_file_type("anything.exe")
    assert ok is True
    assert reason == ""


def test_validate_file_size_missing_file_is_ok() -> None:
    ok, reason = FSIsolationManager().validate_file_size("/no/such/file_xyz.bin")
    assert ok is True
    assert reason == ""


def test_validate_file_size_ok(tmp_path: Path) -> None:
    target = tmp_path / "small.txt"
    target.write_text("hi", encoding="utf-8")
    ok, reason = FSIsolationManager().validate_file_size(str(target))
    assert ok is True
    assert reason == ""


def test_validate_file_size_too_large(tmp_path: Path) -> None:
    target = tmp_path / "big.txt"
    target.write_text("hello", encoding="utf-8")
    manager = _manager(max_file_size_mb=0)
    ok, reason = manager.validate_file_size(str(target))
    assert ok is False
    assert "File too large" in reason


# ── _is_blocked / _is_allowed / _contains_traversal ─────────────────────


def test_is_blocked_wildcard_fnmatch_and_prefix() -> None:
    manager = FSIsolationManager()
    # fnmatch against the default "/home/*/.ssh" pattern
    assert manager._is_blocked(Path("/home/alice/.ssh")) is True
    # wildcard pattern whose prefix matches although fnmatch does not
    manager2 = _manager(blocked_paths=["/var/*/data"])
    assert manager2._is_blocked(Path("/var/foo/other")) is True


def test_is_blocked_exact_and_child_prefix() -> None:
    manager = FSIsolationManager()
    assert manager._is_blocked(Path("/etc/shadow")) is True
    assert manager._is_blocked(Path("/etc/shadow/child")) is True
    assert manager._is_blocked(Path("/tmp/definitely/allowed")) is False


def test_is_allowed_skips_unresolvable_entries() -> None:
    manager = _manager(allowed_paths=["/tmp/\0bad"])
    assert manager._is_allowed(Path("/tmp/x")) is False


def test_contains_traversal() -> None:
    manager = FSIsolationManager()
    assert manager._contains_traversal("a/../b") is True
    assert manager._contains_traversal("a\\..\\b") is True
    assert manager._contains_traversal("a/./b") is False
