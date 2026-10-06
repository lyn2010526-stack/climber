"""Coverage tests for app.core.file_patch.

Exercises diff generation, preview, validation and the pure-Python unified
diff applier (including multi-hunk, CRLF and malformed patches).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.file_patch import (
    EditValidationError,
    FilePatchService,
    get_current_agent_mode,
    set_current_agent_mode,
)


def _write(tmp_path: Path, name: str, content: str) -> str:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return str(path)


# ── context-local agent mode ────────────────────────────────────────────


def test_agent_mode_context_roundtrip() -> None:
    assert get_current_agent_mode() is None
    set_current_agent_mode("PLAN")
    assert get_current_agent_mode() == "PLAN"
    set_current_agent_mode(None)
    assert get_current_agent_mode() is None


def test_edit_validation_error_is_exception() -> None:
    assert issubclass(EditValidationError, Exception)
    err = EditValidationError("bad")
    assert str(err) == "bad"


# ── create_patch ────────────────────────────────────────────────────────


def test_create_patch_uses_default_labels_and_reports_change() -> None:
    diff = FilePatchService.create_patch("a\n", "b\n")
    assert "--- a" in diff
    assert "+++ b" in diff
    assert "-a" in diff
    assert "+b" in diff


def test_create_patch_uses_file_path_label() -> None:
    diff = FilePatchService.create_patch("one\ntwo\n", "one\nthree\n", "notes.txt")
    assert "--- notes.txt" in diff
    assert "+++ notes.txt" in diff


def test_create_patch_identical_content_is_empty() -> None:
    assert FilePatchService.create_patch("same\n", "same\n") == ""


# ── preview_edit ────────────────────────────────────────────────────────


def test_preview_edit_success(tmp_path: Path) -> None:
    path = _write(tmp_path, "f.txt", "hello world\n")
    diff, message = FilePatchService.preview_edit(path, "world", "there")
    assert message == "Preview generated"
    assert "-hello world" in diff
    assert "+hello there" in diff


def test_preview_edit_old_string_missing(tmp_path: Path) -> None:
    path = _write(tmp_path, "f.txt", "hello\n")
    diff, message = FilePatchService.preview_edit(path, "absent", "x")
    assert diff == ""
    assert "old_string not found" in message


def test_preview_edit_io_error() -> None:
    diff, message = FilePatchService.preview_edit("/no/such/file_xyz.txt", "a", "b")
    assert diff == ""
    assert message.startswith("Error previewing edit:")


# ── validate_edit ───────────────────────────────────────────────────────


def test_validate_edit_missing_file() -> None:
    valid, message = FilePatchService.validate_edit("/no/such/file_xyz.txt", "abc", "def")
    assert valid is False
    assert message.startswith("File not found:")


def test_validate_edit_old_string_missing(tmp_path: Path) -> None:
    path = _write(tmp_path, "f.txt", "content here\n")
    valid, message = FilePatchService.validate_edit(path, "zzz", "y")
    assert valid is False
    assert "old_string not found" in message


def test_validate_edit_rejects_too_short(tmp_path: Path) -> None:
    path = _write(tmp_path, "f.txt", "ab plus more\n")
    valid, message = FilePatchService.validate_edit(path, "ab", "xy")
    assert valid is False
    assert "too short" in message


def test_validate_edit_rejects_ambiguous(tmp_path: Path) -> None:
    path = _write(tmp_path, "f.txt", "abc" * 101 + "\n")
    valid, message = FilePatchService.validate_edit(path, "abc", "xyz")
    assert valid is False
    assert "appears 101 times" in message


def test_validate_edit_accepts_unique(tmp_path: Path) -> None:
    path = _write(tmp_path, "f.txt", "unique token here\n")
    valid, message = FilePatchService.validate_edit(path, "unique token", "other")
    assert valid is True
    assert message == "Edit is valid"


def test_validate_edit_io_error(tmp_path: Path) -> None:
    directory = tmp_path / "adir"
    directory.mkdir()
    valid, message = FilePatchService.validate_edit(str(directory), "abc", "def")
    assert valid is False
    assert message.startswith("Error validating edit:")


# ── _apply_unified_diff ─────────────────────────────────────────────────


def test_apply_unified_diff_single_hunk() -> None:
    old = "alpha\nbeta\ngamma\n"
    new = "alpha\nBETA\ngamma\n"
    patch = FilePatchService.create_patch(old, new, "f.txt")
    assert FilePatchService._apply_unified_diff(old, patch) == new


def test_apply_unified_diff_multiple_hunks_reversed_order() -> None:
    old = "".join(f"{i}\n" for i in range(1, 13))
    patch = "--- f\n+++ f\n@@ -1,3 +1,3 @@\n 1\n-2\n+X\n 3\n@@ -10,3 +10,3 @@\n 10\n-11\n+Y\n 12\n"
    result = FilePatchService._apply_unified_diff(old, patch)
    assert result == "1\nX\n3\n4\n5\n6\n7\n8\n9\n10\nY\n12\n"


def test_apply_unified_diff_insertion() -> None:
    old = "a\nb\n"
    new = "a\ninserted\nb\n"
    patch = FilePatchService.create_patch(old, new, "f.txt")
    assert FilePatchService._apply_unified_diff(old, patch) == new


def test_apply_unified_diff_crlf_detection() -> None:
    old = "a\r\nb\r\n"
    new = "a\r\nB\r\n"
    patch = FilePatchService.create_patch(old, new, "f.txt")
    assert FilePatchService._apply_unified_diff(old, patch) == new


def test_apply_unified_diff_no_hunks_returns_none() -> None:
    assert FilePatchService._apply_unified_diff("a\n", "not a diff at all") is None


def test_apply_unified_diff_malformed_header_raises_keyerror() -> None:
    # A hunk marker that fails the regex yields a hunk dict with no
    # old_start/old_count, which then raises KeyError during application.
    patch = "--- a\n+++ b\n@@ this is not a valid header @@\n"
    with pytest.raises(KeyError):
        FilePatchService._apply_unified_diff("x\n", patch)


def test_apply_unified_diff_content_without_trailing_newline() -> None:
    # no line ends with "\n" so the line-ending detection loop is exhausted
    patch = "--- a\n+++ b\n@@ -1,1 +1,1 @@\n-abc\n+X\n"
    assert FilePatchService._apply_unified_diff("abc", patch) == "X\n"


def test_apply_unified_diff_skips_unknown_prefix_lines() -> None:
    old = "keep\n"
    patch = "--- a\n+++ b\n@@ -1,1 +1,1 @@\n\\ No newline at end of file\n keep\n"
    result = FilePatchService._apply_unified_diff(old, patch)
    assert result is not None


# ── apply_patch_to_file ─────────────────────────────────────────────────


def test_apply_patch_to_file_missing_file() -> None:
    ok, message = FilePatchService.apply_patch_to_file("/no/such/file_xyz.txt", "@@")
    assert ok is False
    assert message.startswith("File not found:")


def test_apply_patch_to_file_success(tmp_path: Path) -> None:
    path = _write(tmp_path, "f.txt", "alpha\nbeta\n")
    patch = FilePatchService.create_patch("alpha\nbeta\n", "alpha\nBETA\n", path)
    ok, message = FilePatchService.apply_patch_to_file(path, patch)
    assert ok is True
    assert "Patch applied successfully" in message
    assert Path(path).read_text(encoding="utf-8") == "alpha\nBETA\n"


def test_apply_patch_to_file_unparseable(tmp_path: Path) -> None:
    path = _write(tmp_path, "f.txt", "alpha\n")
    ok, message = FilePatchService.apply_patch_to_file(path, "garbage without hunks")
    assert ok is False
    assert "could not parse or apply patch" in message


def test_apply_patch_to_file_exception_path(tmp_path: Path) -> None:
    # a directory exists but is not a regular file -> read/open raises
    directory = tmp_path / "adir"
    directory.mkdir()
    ok, message = FilePatchService.apply_patch_to_file(str(directory), "@@ -1 +1 @@\n-x\n+y\n")
    assert ok is False
    assert message.startswith("Error applying patch:")
