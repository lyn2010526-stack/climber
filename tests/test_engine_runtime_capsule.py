"""Tests for runtime state capsule."""

import os
import tempfile

import pytest

from app.core.engine.runtime_capsule import (
    BlockingFact,
    FileCategory,
    FileState,
    RuntimeStateCapsule,
    ToolReceipt,
    WorkspaceSnapshot,
)


class TestRuntimeStateCapsule:
    def test_classify_source_file(self) -> None:
        capsule = RuntimeStateCapsule()
        assert capsule.classify_file("app/main.py") == FileCategory.SOURCE
        assert capsule.classify_file("src/index.ts") == FileCategory.SOURCE
        assert capsule.classify_file("lib/utils.go") == FileCategory.SOURCE

    def test_classify_test_file(self) -> None:
        capsule = RuntimeStateCapsule()
        assert capsule.classify_file("test_main.py") == FileCategory.TEST
        assert capsule.classify_file("tests/test_utils.py") == FileCategory.TEST
        assert capsule.classify_file("src/component.test.ts") == FileCategory.TEST

    def test_classify_scratch_file(self) -> None:
        capsule = RuntimeStateCapsule()
        assert capsule.classify_file("/tmp/temp_file.txt") == FileCategory.SCRATCH
        assert capsule.classify_file("notes_scratch.md") == FileCategory.SCRATCH

    def test_classify_config_file(self) -> None:
        capsule = RuntimeStateCapsule()
        assert capsule.classify_file("config.json") == FileCategory.CONFIG
        assert capsule.classify_file("settings.yaml") == FileCategory.CONFIG

    def test_classify_unknown_file(self) -> None:
        capsule = RuntimeStateCapsule()
        assert capsule.classify_file("README") == FileCategory.UNKNOWN

    def test_add_receipt(self) -> None:
        capsule = RuntimeStateCapsule()
        receipt = ToolReceipt(
            tool_name="edit_file",
            files_affected=["app/main.py"],
            success=True,
            duration_ms=50.0,
        )
        capsule.add_receipt(receipt)
        assert len(capsule._receipts) == 1
        assert capsule._receipts[0].tool_name == "edit_file"

    def test_add_receipt_size_cap(self) -> None:
        capsule = RuntimeStateCapsule()
        for i in range(250):
            capsule.add_receipt(ToolReceipt(tool_name=f"tool_{i}"))
        assert len(capsule._receipts) <= 200

    def test_get_files_by_category(self) -> None:
        capsule = RuntimeStateCapsule()
        capsule._files = {
            "app/main.py": FileState("app/main.py", FileCategory.SOURCE),
            "test_main.py": FileState("test_main.py", FileCategory.TEST),
            "config.json": FileState("config.json", FileCategory.CONFIG),
        }
        sources = capsule.get_files_by_category(FileCategory.SOURCE)
        assert len(sources) == 1
        assert sources[0].path == "app/main.py"

    def test_get_blocking_facts_no_snapshots(self) -> None:
        capsule = RuntimeStateCapsule()
        assert capsule.get_blocking_facts() == []

    def test_get_stats(self) -> None:
        capsule = RuntimeStateCapsule()
        capsule._files = {
            "app/main.py": FileState("app/main.py", FileCategory.SOURCE),
            "test_main.py": FileState("test_main.py", FileCategory.TEST),
        }
        stats = capsule.get_stats()
        assert stats["total_files"] == 2
        assert "source" in stats["categories"]
        assert "test" in stats["categories"]


class TestBlockingFact:
    def test_creation(self) -> None:
        fact = BlockingFact(
            description="Scratch files without source",
            severity="warning",
            related_files=["/tmp/notes.txt"],
            suggestion="Review scratch files",
        )
        assert fact.severity == "warning"
        assert len(fact.related_files) == 1


class TestFileState:
    def test_creation(self) -> None:
        state = FileState(
            path="app/main.py",
            category=FileCategory.SOURCE,
            size_bytes=1024,
            change_type="modified",
        )
        assert state.path == "app/main.py"
        assert state.category == FileCategory.SOURCE
        assert state.size_bytes == 1024


class TestToolReceipt:
    def test_creation(self) -> None:
        receipt = ToolReceipt(
            tool_name="edit_file",
            arguments={"path": "main.py"},
            files_affected=["main.py"],
            success=True,
            duration_ms=25.0,
        )
        assert receipt.tool_name == "edit_file"
        assert receipt.success is True
        assert receipt.arguments["path"] == "main.py"


class TestWorkspaceSnapshot:
    def test_to_dict(self) -> None:
        snapshot = WorkspaceSnapshot(
            files={"app/main.py": FileState("app/main.py", FileCategory.SOURCE, size_bytes=500)},
            blocking_facts=[
                BlockingFact(description="test fact", severity="info"),
            ],
        )
        d = snapshot.to_dict()
        assert "app/main.py" in d["files"]
        assert len(d["blocking_facts"]) == 1
        assert d["receipts_count"] == 0
