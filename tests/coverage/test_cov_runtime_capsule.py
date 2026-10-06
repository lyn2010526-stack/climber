"""Coverage tests for app.core.engine.runtime_capsule."""

from __future__ import annotations

import subprocess
from typing import Any

from app.core.engine.runtime_capsule import (
    BlockingFact,
    FileCategory,
    FileState,
    RuntimeStateCapsule,
    ToolReceipt,
    WorkspaceSnapshot,
)


def test_classify_file_categories(tmp_path: Any) -> None:
    cap = RuntimeStateCapsule(workdir=str(tmp_path))
    assert cap.classify_file("src/main.py") is FileCategory.SOURCE
    assert cap.classify_file("a/b/Component.tsx") is FileCategory.SOURCE
    assert cap.classify_file("tests/test_thing.py") is FileCategory.TEST
    assert cap.classify_file("foo_test.py") is FileCategory.TEST
    assert cap.classify_file("app.spec.ts") is FileCategory.TEST
    assert cap.classify_file("settings.yaml") is FileCategory.CONFIG
    assert cap.classify_file("/tmp/scratch.py") is FileCategory.SCRATCH
    assert cap.classify_file("temp_notes.md") is FileCategory.SCRATCH
    assert cap.classify_file("README.md") is FileCategory.UNKNOWN


def test_classify_scratch_wins_over_test() -> None:
    cap = RuntimeStateCapsule(workdir="/tmp")
    assert cap.classify_file("/tmp/test_x.py") is FileCategory.SCRATCH


def test_default_workdir_uses_cwd() -> None:
    cap = RuntimeStateCapsule()
    assert cap._workdir


def _fake_run(stdout: str, returncode: int = 0) -> Any:
    def _run(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout)

    return _run


def test_scan_files_parses_git_status(tmp_path: Any, monkeypatch: Any) -> None:
    real = tmp_path / "main.py"
    real.write_text("x" * 42)
    stdout = f"?? new.py\n M src/main.py\n M {real}\n D gone.py\n\n"
    monkeypatch.setattr(subprocess, "run", _fake_run(stdout))
    cap = RuntimeStateCapsule(workdir=str(tmp_path))
    files = cap._scan_files()
    assert files["new.py"].change_type == "added"
    assert files["src/main.py"].change_type == "modified"
    assert files["gone.py"].change_type == "deleted"
    assert files["gone.py"].size_bytes == 0
    abspath = str(real)
    assert files[abspath].size_bytes == 42
    assert files["src/main.py"].category is FileCategory.SOURCE
    assert cap._files is files


def test_scan_files_git_failure_yields_empty(tmp_path: Any, monkeypatch: Any) -> None:
    monkeypatch.setattr(subprocess, "run", _fake_run("garbage", returncode=128))
    cap = RuntimeStateCapsule(workdir=str(tmp_path))
    assert cap._scan_files() == {}


def test_scan_files_missing_git(tmp_path: Any, monkeypatch: Any) -> None:
    def _raise(*_a: Any, **_k: Any) -> Any:
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", _raise)
    cap = RuntimeStateCapsule(workdir=str(tmp_path))
    assert cap._scan_files() == {}


def test_scan_files_stat_error_is_swallowed(tmp_path: Any, monkeypatch: Any) -> None:
    target = tmp_path / "m.py"
    target.write_text("hello")
    monkeypatch.setattr(subprocess, "run", _fake_run(f"?? seed.txt\n M {target}\n"))
    monkeypatch.setattr("app.core.engine.runtime_capsule.os.path.exists", lambda _p: True)

    def _bad_stat(*_a: Any, **_k: Any) -> Any:
        raise OSError("nope")

    monkeypatch.setattr("app.core.engine.runtime_capsule.os.stat", _bad_stat)
    cap = RuntimeStateCapsule(workdir=str(tmp_path))
    files = cap._scan_files()
    assert files[str(target)].size_bytes == 0


def test_detect_blocking_facts_scratch_without_source() -> None:
    cap = RuntimeStateCapsule(workdir="/tmp")
    files = {
        "a": FileState(path="/tmp/a", category=FileCategory.SCRATCH),
        "b": FileState(path="/tmp/b", category=FileCategory.SCRATCH),
    }
    facts = cap._detect_blocking_facts(files)
    assert len(facts) == 1
    assert facts[0].severity == "warning"
    assert "2 scratch file(s)" in facts[0].description
    assert set(facts[0].related_files) == {"/tmp/a", "/tmp/b"}


def test_detect_blocking_facts_source_without_tests_over_threshold() -> None:
    cap = RuntimeStateCapsule(workdir="/tmp")
    files = {
        f"s{i}": FileState(path=f"src/mod{i}.py", category=FileCategory.SOURCE) for i in range(3)
    }
    facts = cap._detect_blocking_facts(files)
    assert len(facts) == 1
    assert facts[0].severity == "info"
    assert "3 source file(s)" in facts[0].description


def test_detect_blocking_facts_source_without_tests_below_threshold() -> None:
    cap = RuntimeStateCapsule()
    files = {
        "a": FileState(path="src/a.py", category=FileCategory.SOURCE),
        "b": FileState(path="src/utils.py", category=FileCategory.SOURCE),
        "c": FileState(path="src/config.py", category=FileCategory.SOURCE),
    }
    # 'util'/'config' are excluded, leaving one prod source -> no fact.
    assert cap._detect_blocking_facts(files) == []


def test_detect_blocking_facts_large_change_set() -> None:
    cap = RuntimeStateCapsule()
    files = {
        f"t{i}": FileState(path=f"test_{i}.py", category=FileCategory.TEST, change_type="modified")
        for i in range(16)
    }
    facts = cap._detect_blocking_facts(files)
    assert len(facts) == 1
    assert "16 files modified" in facts[0].description
    assert len(facts[0].related_files) == 10


def test_capture_appends_snapshot_and_getters(tmp_path: Any, monkeypatch: Any) -> None:
    monkeypatch.setattr(subprocess, "run", _fake_run("?? src/x.py\n"))
    cap = RuntimeStateCapsule(workdir=str(tmp_path))
    snap = cap.capture()
    assert isinstance(snap, WorkspaceSnapshot)
    assert cap.get_blocking_facts() == snap.blocking_facts
    assert len(cap._snapshots) == 1
    stats = cap.get_stats()
    assert stats["total_files"] == 1
    assert stats["snapshots_count"] == 1
    assert stats["categories"] == {"source": 1}


def test_get_blocking_facts_before_capture_is_empty() -> None:
    cap = RuntimeStateCapsule()
    assert cap.get_blocking_facts() == []


def test_get_stats_scans_when_empty(monkeypatch: Any, tmp_path: Any) -> None:
    monkeypatch.setattr(subprocess, "run", _fake_run(""))
    cap = RuntimeStateCapsule(workdir=str(tmp_path))
    assert cap._files == {}
    stats = cap.get_stats()
    assert stats["total_files"] == 0
    assert stats["categories"] == {}


def test_add_receipt_and_trimming() -> None:
    cap = RuntimeStateCapsule()
    for _ in range(200):
        cap.add_receipt(ToolReceipt(tool_name="t"))
    assert len(cap._receipts) == 200
    cap.add_receipt(ToolReceipt(tool_name="t"))
    assert len(cap._receipts) == 100


def test_get_files_by_category() -> None:
    cap = RuntimeStateCapsule()
    cap._files = {
        "a": FileState(path="a", category=FileCategory.SOURCE),
        "b": FileState(path="b", category=FileCategory.TEST),
    }
    assert [f.path for f in cap.get_files_by_category(FileCategory.SOURCE)] == ["a"]


def test_workspace_snapshot_to_dict() -> None:
    snap = WorkspaceSnapshot(
        files={"a.py": FileState(path="a.py", category=FileCategory.SOURCE, size_bytes=5)},
        receipts=[ToolReceipt(tool_name="t")],
        blocking_facts=[BlockingFact(description="d", related_files=["a.py"])],
    )
    data = snap.to_dict()
    assert data["files"]["a.py"]["category"] == "source"
    assert data["receipts_count"] == 1
    assert data["blocking_facts"][0]["description"] == "d"


def test_dataclass_defaults() -> None:
    fs = FileState(path="p")
    assert fs.category is FileCategory.UNKNOWN
    assert fs.change_type == "modified"
    rec = ToolReceipt(tool_name="t")
    assert rec.success is True
    assert rec.files_affected == []
    bf = BlockingFact(description="d")
    assert bf.severity == "warning"
    assert bf.suggestion == ""
