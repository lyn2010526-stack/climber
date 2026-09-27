"""Tests for MemFS path containment and git-history scoping."""

from __future__ import annotations

import pytest

from app.core.memfs.store import MemFS


@pytest.fixture
def memfs(tmp_path):
    return MemFS(str(tmp_path / "memfs"), auto_commit=False)


class TestPathContainment:
    def test_accepts_nested_relative_path(self, memfs):
        resolved = memfs._resolve_path("system/persona.md")
        assert resolved.is_relative_to(memfs.base_path)

    def test_accepts_current_directory(self, memfs):
        assert memfs._resolve_path(".") == memfs.base_path

    @pytest.mark.parametrize(
        "candidate",
        [
            "../outside.md",
            "../../etc/passwd",
            "system/../../escape.md",
        ],
    )
    def test_rejects_traversal(self, memfs, candidate):
        with pytest.raises(ValueError, match="Path traversal"):
            memfs._resolve_path(candidate)

    def test_rejects_sibling_directory_with_shared_prefix(self, memfs, tmp_path):
        """A sibling whose name starts with the base name is outside the tree."""
        sibling = memfs.base_path.parent / f"{memfs.base_path.name}-secrets"
        sibling.mkdir(parents=True, exist_ok=True)
        target = sibling / "secret.md"
        target.write_text("leaked", encoding="utf-8")

        with pytest.raises(ValueError, match="Path traversal"):
            memfs._resolve_path(f"../{memfs.base_path.name}-secrets/secret.md")

    def test_rejects_absolute_path_outside_base(self, memfs, tmp_path):
        outside = tmp_path / "outside.md"
        outside.write_text("leaked", encoding="utf-8")
        with pytest.raises(ValueError, match="Path traversal"):
            memfs._resolve_path(str(outside))


class TestHistoryScoping:
    async def test_history_of_sibling_path_is_empty(self, memfs):
        sibling = memfs.base_path.parent / f"{memfs.base_path.name}-secrets"
        sibling.mkdir(parents=True, exist_ok=True)
        (sibling / "secret.md").write_text("leaked", encoding="utf-8")

        assert await memfs.get_history(f"../{memfs.base_path.name}-secrets/secret.md") == []

    async def test_history_of_traversal_path_is_empty(self, memfs):
        assert await memfs.get_history("../../etc/passwd") == []


class TestGitAvailability:
    def test_reports_git_disabled_when_binary_missing(self, monkeypatch, tmp_path):
        monkeypatch.setattr("app.core.memfs.store._GIT_BIN", None)
        store = MemFS(str(tmp_path / "nogit"), auto_commit=False)
        assert store.git_enabled is False

    def test_existing_repo_enables_git(self, tmp_path):
        store = MemFS(str(tmp_path / "withgit"), auto_commit=False)
        assert isinstance(store.git_enabled, bool)
