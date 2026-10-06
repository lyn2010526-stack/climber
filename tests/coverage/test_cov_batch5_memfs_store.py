"""Coverage tests for app/core/memfs/store.py (git-backed MemFS)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

import app.core.memfs.store as store_module
from app.core.memfs.memory_block import MemoryBlock
from app.core.memfs.store import DEFAULT_SYSTEM_FILES, MemFS


@pytest.fixture
def git_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Give git an identity so commits succeed without global config."""
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Cov Test")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "cov@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Cov Test")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "cov@example.com")


async def test_write_read_append_delete_roundtrip(tmp_path: Path, git_identity: None) -> None:
    memfs = MemFS(str(tmp_path))
    assert memfs.git_enabled is (shutil.which("git") is not None)
    assert memfs.base_path == tmp_path.resolve()

    await memfs.write("system/persona.md", "You are helpful.")
    assert await memfs.exists("system/persona.md") is True
    assert await memfs.read("system/persona.md") == "You are helpful."

    block = await memfs.read_block("system/persona.md")
    assert isinstance(block, MemoryBlock)
    assert block.content == "You are helpful."

    await memfs.append("system/persona.md", "Be concise.")
    content = await memfs.read("system/persona.md")
    assert "You are helpful." in content
    assert "Be concise." in content

    await memfs.delete("system/persona.md")
    assert await memfs.exists("system/persona.md") is False


async def test_write_preserves_existing_metadata(tmp_path: Path, git_identity: None) -> None:
    memfs = MemFS(str(tmp_path))
    first = MemoryBlock.new(path="reference/notes.md", content="v1", importance=0.9)
    await memfs.write_block(first)
    # Overwrite via write(): frontmatter metadata should be preserved
    await memfs.write("reference/notes.md", "v2")
    block = await memfs.read_block("reference/notes.md")
    assert block.content == "v2"
    assert block.metadata.get("importance") == 0.9


async def test_read_missing_raises(tmp_path: Path, git_identity: None) -> None:
    memfs = MemFS(str(tmp_path))
    with pytest.raises(FileNotFoundError):
        await memfs.read("system/missing.md")
    with pytest.raises(FileNotFoundError):
        await memfs.read_block("system/missing.md")
    with pytest.raises(FileNotFoundError):
        await memfs.delete("system/missing.md")


async def test_read_returns_raw_when_parse_fails(
    tmp_path: Path, git_identity: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    memfs = MemFS(str(tmp_path))
    target = tmp_path / "raw.md"
    target.write_text("raw body", encoding="utf-8")

    def boom(*args, **kwargs):
        raise ValueError("cannot parse")

    monkeypatch.setattr(
        "app.core.memfs.store.MemoryBlock", type("X", (), {"from_markdown": staticmethod(boom)})
    )
    assert await memfs.read("raw.md") == "raw body"


async def test_path_traversal_rejected(tmp_path: Path, git_identity: None) -> None:
    memfs = MemFS(str(tmp_path))
    with pytest.raises(ValueError, match="Path traversal"):
        await memfs.read("../escape.txt")


async def test_list_prefix_variants(tmp_path: Path, git_identity: None) -> None:
    memfs = MemFS(str(tmp_path))
    await memfs.write("system/persona.md", "p")
    await memfs.write("reference/notes.md", "n")

    all_files = await memfs.list()
    assert "system/persona.md" in all_files
    assert "reference/notes.md" in all_files

    only_system = await memfs.list("system/")
    assert only_system == ["system/persona.md"]

    # prefix points at a single file
    assert await memfs.list("reference/notes.md") == ["reference/notes.md"]
    # prefix points at nothing
    assert await memfs.list("does/not/exist/") == []


async def test_list_skips_hidden_and_pycache(tmp_path: Path, git_identity: None) -> None:
    memfs = MemFS(str(tmp_path))
    await memfs.write("visible.md", "v")
    (tmp_path / ".hidden.md").write_text("h", encoding="utf-8")
    pycache = tmp_path / "__pycache__"
    pycache.mkdir()
    (pycache / "x.pyc").write_bytes(b"\x00")
    (tmp_path / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")

    listed = await memfs.list()
    assert "visible.md" in listed
    assert ".hidden.md" not in listed
    assert not any("__pycache__" in p for p in listed)
    assert ".gitignore" in listed


async def test_get_tree_structure(tmp_path: Path, git_identity: None) -> None:
    memfs = MemFS(str(tmp_path))
    await memfs.write("system/persona.md", "p")
    await memfs.write("skills/demo/SKILL.md", "s")
    (tmp_path / ".secret").write_text("x", encoding="utf-8")

    tree = await memfs.get_tree()
    assert "system" in tree["_dirs"]
    assert "skills" in tree["_dirs"]
    person = next(f for f in tree["_dirs"]["system"]["_files"] if f["path"] == "system/persona.md")
    assert person["size"] > 0
    assert "modified" in person
    # hidden entries are skipped
    assert all(".secret" not in f["path"] for f in tree["_files"])
    assert ".secret" not in tree["_dirs"]


async def test_get_tree_missing_dir(tmp_path: Path, git_identity: None) -> None:
    memfs = MemFS(str(tmp_path))
    tree = memfs._build_tree(tmp_path / "nope")
    assert tree == {"_files": [], "_dirs": {}}


async def test_search_and_truncation(tmp_path: Path, git_identity: None) -> None:
    memfs = MemFS(str(tmp_path))
    many = "\n".join(f"line banner number {i}" for i in range(15))
    (tmp_path / "big.md").write_text(many, encoding="utf-8")
    await memfs.write("system/other.md", "nothing relevant here")

    results = await memfs.search("BANNER")
    assert len(results) == 1
    match = results[0]
    assert match["path"] == "big.md"
    assert match["total_matches"] == 15
    assert len(match["matches"]) == 10  # capped
    assert match["matches"][0].startswith("L1: line banner")

    assert await memfs.search("zzz-not-present") == []


async def test_search_skips_undecodable_file(tmp_path: Path, git_identity: None) -> None:
    memfs = MemFS(str(tmp_path))
    (tmp_path / "binary.md").write_bytes(b"\xff\xfe\x00\x01target")
    await memfs.write("text.md", "target text")

    results = await memfs.search("target")
    paths = {r["path"] for r in results}
    assert "binary.md" not in paths
    assert "text.md" in paths


async def test_init_defaults_and_idempotent(tmp_path: Path, git_identity: None) -> None:
    memfs = MemFS(str(tmp_path))
    created = await memfs.init_defaults()
    assert set(created) == set(DEFAULT_SYSTEM_FILES)
    assert await memfs.init_defaults() == []
    persona = await memfs.read("system/persona.md")
    assert "Agent identity" in persona


async def test_append_creates_new_file(tmp_path: Path, git_identity: None) -> None:
    # NOTE: append() does not mkdir the parent (unlike write()/write_block()),
    # so a brand-new nested path raises FileNotFoundError. See report.
    memfs = MemFS(str(tmp_path))
    await memfs.append("notes.md", "first")
    content = await memfs.read("notes.md")
    assert content == "first"


async def test_append_new_nested_path_requires_existing_parent(
    tmp_path: Path, git_identity: None
) -> None:
    memfs = MemFS(str(tmp_path))
    with pytest.raises(FileNotFoundError):
        await memfs.append("conversations/notes.md", "first")
    # Once the parent exists, append works.
    (tmp_path / "conversations").mkdir()
    await memfs.append("conversations/notes.md", "first")
    assert await memfs.read("conversations/notes.md") == "first"


async def test_append_falls_back_when_parse_fails(
    tmp_path: Path, git_identity: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    memfs = MemFS(str(tmp_path))
    target = tmp_path / "raw.md"
    target.write_text("original", encoding="utf-8")

    def boom(*args, **kwargs):
        raise ValueError("cannot parse")

    monkeypatch.setattr(
        "app.core.memfs.store.MemoryBlock",
        type("X", (), {"from_markdown": staticmethod(boom)}),
    )
    await memfs.append("raw.md", "appended")
    assert target.read_text(encoding="utf-8").strip() == "original\nappended"


async def test_append_to_existing_without_frontmatter_fallback(
    tmp_path: Path, git_identity: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Second branch of the same fallback path: append twice with a broken parser.
    memfs = MemFS(str(tmp_path))
    target = tmp_path / "raw2.md"
    target.write_text("base", encoding="utf-8")

    def boom(*args, **kwargs):
        raise ValueError("cannot parse")

    monkeypatch.setattr(
        "app.core.memfs.store.MemoryBlock",
        type("X", (), {"from_markdown": staticmethod(boom)}),
    )
    await memfs.append("raw2.md", "one")
    await memfs.append("raw2.md", "two")
    assert "one" in target.read_text(encoding="utf-8")
    assert "two" in target.read_text(encoding="utf-8")


async def test_get_history_after_commit(tmp_path: Path, git_identity: None) -> None:
    memfs = MemFS(str(tmp_path))
    if not memfs.git_enabled:
        pytest.skip("git not available")
    await memfs.write("system/history.md", "v1")
    await memfs.write("system/history.md", "v2")
    history = await memfs.get_history("system/history.md", limit=10)
    assert history
    entry = history[0]
    assert set(entry) == {"hash", "date", "author", "message"}
    assert len(entry["hash"]) == 12

    # Unknown path -> empty list
    assert await memfs.get_history("system/none.md") == []


async def test_reinit_existing_repo_is_noop(tmp_path: Path, git_identity: None) -> None:
    first = MemFS(str(tmp_path))
    assert first.git_enabled is True
    second = MemFS(str(tmp_path))
    assert second.git_enabled is True


async def test_pre_existing_gitignore(tmp_path: Path, git_identity: None) -> None:
    (tmp_path / ".gitignore").write_text("custom\n", encoding="utf-8")
    memfs = MemFS(str(tmp_path))
    assert memfs.git_enabled is True
    assert (tmp_path / ".gitignore").read_text(encoding="utf-8") == "custom\n"


async def test_git_disabled_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.memfs.store.shutil.which", lambda name: None)
    memfs = MemFS(str(tmp_path))
    assert memfs.git_enabled is False
    # write still works, commits skipped
    await memfs.write("system/x.md", "x")
    assert await memfs.get_history("system/x.md") == []
    await memfs.delete("system/x.md")


async def test_init_git_failure_disables_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def raiser(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="git", timeout=1)

    monkeypatch.setattr("app.core.memfs.store.subprocess.run", raiser)
    memfs = MemFS(str(tmp_path))
    assert memfs.git_enabled is False


async def test_git_commit_failure_is_swallowed(
    tmp_path: Path, git_identity: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    memfs = MemFS(str(tmp_path))
    warnings: list[str] = []

    def raiser(*args, **kwargs):
        warnings.append("called")
        raise OSError("git gone")

    monkeypatch.setattr("app.core.memfs.store.subprocess.run", raiser)
    await memfs.write("system/y.md", "y")  # must not raise
    await memfs.delete("system/y.md")
    assert warnings


async def test_write_parse_failure_creates_new_block(
    tmp_path: Path, git_identity: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    memfs = MemFS(str(tmp_path))
    (tmp_path / "broken.md").write_text("---\n: : bad\n---\nx", encoding="utf-8")

    def boom(cls, path, md):
        raise ValueError("cannot parse")

    monkeypatch.setattr(store_module.MemoryBlock, "from_markdown", classmethod(boom))
    await memfs.write("broken.md", "recovered")
    # from_markdown is patched to raise, so read() returns the raw file text
    assert "recovered" in await memfs.read("broken.md")


async def test_auto_commit_disabled(tmp_path: Path, git_identity: None) -> None:
    memfs = MemFS(str(tmp_path), auto_commit=False)
    await memfs.write("system/a.md", "a")
    await memfs.write_block(MemoryBlock.new(path="system/b.md", content="b"))
    await memfs.append("system/a.md", "more")
    await memfs.delete("system/b.md")
    assert await memfs.read("system/a.md") == "a\nmore"
    assert await memfs.exists("system/b.md") is False


async def test_append_fallback_with_auto_commit_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    memfs = MemFS(str(tmp_path), auto_commit=False)
    target = tmp_path / "raw3.md"
    target.write_text("base", encoding="utf-8")

    def boom(*args, **kwargs):
        raise ValueError("cannot parse")

    monkeypatch.setattr(store_module.MemoryBlock, "from_markdown", classmethod(boom))
    await memfs.append("raw3.md", "appended")
    assert target.read_text(encoding="utf-8").strip() == "base\nappended"


async def test_get_tree_permission_error(
    tmp_path: Path, git_identity: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    memfs = MemFS(str(tmp_path))

    def boom(self):
        raise PermissionError("nope")

    monkeypatch.setattr(Path, "iterdir", boom)
    tree = await memfs.get_tree()
    assert tree == {"_files": [], "_dirs": {}}


async def test_get_tree_skips_pycache_and_special_entries(
    tmp_path: Path, git_identity: None
) -> None:
    memfs = MemFS(str(tmp_path))
    await memfs.write("plain.md", "x")
    pycache = tmp_path / "__pycache__"
    pycache.mkdir()
    (pycache / "z.pyc").write_bytes(b"\x00")
    # A broken symlink is neither a file nor a directory.
    (tmp_path / "broken_link").symlink_to(tmp_path / "does-not-exist")

    tree = await memfs.get_tree()
    names = {f["path"] for f in tree["_files"]}
    assert "plain.md" in names
    assert "__pycache__" not in tree["_dirs"]
    assert not any("z.pyc" in n for n in names)


async def test_init_git_commit_nonzero_is_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Res:
        def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(args, **kwargs):
        if "rev-parse" in args:
            return _Res(1)  # treat as "not a repo yet"
        if "commit" in args:
            return _Res(1)  # commit fails -> success log skipped
        return _Res(0)

    monkeypatch.setattr(store_module.subprocess, "run", fake_run)
    memfs = MemFS(str(tmp_path))
    assert memfs.git_enabled is True


async def test_get_history_failure_and_malformed(
    tmp_path: Path, git_identity: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    memfs = MemFS(str(tmp_path))

    class _Fail:
        returncode = 1
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr(store_module.subprocess, "run", lambda *a, **k: _Fail())
    assert await memfs.get_history("anything") == []

    class _Malformed:
        returncode = 0
        stdout = "onlyhash|date|author\nhash2|2024-01-01T00:00:00+00:00|me|msg"
        stderr = ""

    monkeypatch.setattr(store_module.subprocess, "run", lambda *a, **k: _Malformed())
    history = await memfs.get_history("anything")
    assert [h["hash"] for h in history] == ["hash2"]


async def test_get_history_timeout(
    tmp_path: Path, git_identity: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    memfs = MemFS(str(tmp_path))

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="git", timeout=1)

    monkeypatch.setattr(store_module.subprocess, "run", timeout)
    assert await memfs.get_history("anything") == []
