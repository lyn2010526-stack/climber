"""Security regression tests for the memory filesystem path boundary."""

from pathlib import Path

import pytest

from app.core.memfs.store import MemFS


def test_memfs_rejects_sibling_prefix_path(tmp_path: Path):
    memfs = MemFS(str(tmp_path / "workspace"), auto_commit=False)

    with pytest.raises(ValueError, match="Path traversal detected"):
        memfs._resolve_path("../workspace-data/secret.txt")


def test_memfs_accepts_path_inside_workspace(tmp_path: Path):
    memfs = MemFS(str(tmp_path / "workspace"), auto_commit=False)

    resolved = memfs._resolve_path("notes/today.md")

    assert resolved == (tmp_path / "workspace" / "notes/today.md").resolve()
