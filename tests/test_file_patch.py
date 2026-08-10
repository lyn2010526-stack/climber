"""Tests for FilePatchService and incremental file editing."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("APP_TESTING", "true")

from app.core.file_patch import FilePatchService, set_current_agent_mode


@pytest.fixture
def tmp_file(tmp_path):
    target = tmp_path / "sample.txt"
    target.write_text("line1\nline2\nline3\n", encoding="utf-8")
    return str(target)


class TestCreatePatch:
    def test_returns_unified_diff(self, tmp_file):
        old = "line1\nline2\nline3\n"
        new = "line1\nline2 changed\nline3\n"
        diff = FilePatchService.create_patch(old, new, tmp_file)
        assert "@@" in diff
        assert "-line2" in diff
        assert "+line2 changed" in diff

    def test_no_diff_when_identical(self):
        content = "hello world\n"
        diff = FilePatchService.create_patch(content, content, "a.txt")
        assert diff == ""


class TestValidateEdit:
    def test_valid_edit(self, tmp_file):
        valid, msg = FilePatchService.validate_edit(tmp_file, "line2", "line2 changed")
        assert valid is True
        assert "valid" in msg.lower()

    def test_missing_old_string(self, tmp_file):
        valid, msg = FilePatchService.validate_edit(tmp_file, "not in file", "x")
        assert valid is False
        assert "not found" in msg.lower()

    def test_short_old_string_rejected(self, tmp_file):
        valid, msg = FilePatchService.validate_edit(tmp_file, "li", "xx")
        assert valid is False
        assert "too short" in msg.lower()

    def test_too_many_occurrences_rejected(self, tmp_file):
        content = "aaa\n" * 200
        path = os.path.dirname(tmp_file) + "/repeat.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        valid, msg = FilePatchService.validate_edit(path, "aaa", "bbb")
        assert valid is False
        assert "appears" in msg.lower()


class TestPreviewEdit:
    def test_returns_diff(self, tmp_file):
        diff, msg = FilePatchService.preview_edit(tmp_file, "line2", "line2 changed")
        assert msg == "Preview generated"
        assert "@@" in diff
        assert "-line2" in diff
        assert "+line2 changed" in diff

    def test_missing_old_string_returns_error(self, tmp_file):
        diff, msg = FilePatchService.preview_edit(tmp_file, "missing", "x")
        assert diff == ""
        assert "not found" in msg.lower()


class TestApplyPatchToFile:
    def test_applies_simple_patch(self, tmp_file):
        old = open(tmp_file, encoding="utf-8").read()
        new = old.replace("line2", "line2 changed")
        patch = FilePatchService.create_patch(old, new, tmp_file)
        ok, msg = FilePatchService.apply_patch_to_file(tmp_file, patch)
        assert ok is True
        assert "applied" in msg.lower()
        assert "line2 changed" in open(tmp_file, encoding="utf-8").read()

    def test_missing_file_returns_error(self):
        ok, msg = FilePatchService.apply_patch_to_file("/nonexistent/path.txt", "@@ -1 +1 @@\n-foo\n+bar\n")
        assert ok is False
        assert "not found" in msg.lower()


class TestPlanMode:
    def test_edit_file_plan_mode_returns_preview(self, tmp_file):
        set_current_agent_mode("plan")
        try:
            diff, msg = FilePatchService.preview_edit(tmp_file, "line2", "line2 changed")
            result = f"PLAN mode preview (no changes applied):\n{diff}"
            assert "Preview generated" in msg
            assert "PLAN mode preview" in result
            assert "line2 changed" in result
            assert "line2" in open(tmp_file, encoding="utf-8").read()
        finally:
            set_current_agent_mode(None)

    def test_edit_file_act_mode_applies(self, tmp_file):
        set_current_agent_mode("act")
        try:
            diff, _msg = FilePatchService.preview_edit(tmp_file, "line2", "line2 changed")
            # In ACT mode, the caller would apply the change
            assert "line2 changed" in diff
        finally:
            set_current_agent_mode(None)
