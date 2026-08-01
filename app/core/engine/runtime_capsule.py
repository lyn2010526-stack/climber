"""Runtime state capsule — reference: OpenSquilla RuntimeStateCapsule.

Tracks workspace state for coding tasks:
- Git dirty files classification: source / test / scratch
- Tool execution receipts (which tool modified which file)
- Blocking fact detection (scratch without source = needs review)
- Workspace diff snapshots for debugging/rollback
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class FileCategory(str, Enum):
    SOURCE = "source"
    TEST = "test"
    SCRATCH = "scratch"
    CONFIG = "config"
    UNKNOWN = "unknown"


@dataclass
class FileState:
    """State of a single file in the workspace."""
    path: str
    category: FileCategory = FileCategory.UNKNOWN
    size_bytes: int = 0
    modified_at: float = 0.0
    change_type: str = "modified"  # added / modified / deleted


@dataclass
class ToolReceipt:
    """Record of a tool execution that modified workspace state."""
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    files_affected: list[str] = field(default_factory=list)
    success: bool = True
    timestamp: float = field(default_factory=time.monotonic)
    duration_ms: float = 0.0


@dataclass
class BlockingFact:
    """A condition that should be reviewed before proceeding."""
    description: str
    severity: str = "warning"  # info / warning / critical
    related_files: list[str] = field(default_factory=list)
    suggestion: str = ""


@dataclass
class WorkspaceSnapshot:
    """Full snapshot of workspace state."""
    files: dict[str, FileState] = field(default_factory=dict)
    receipts: list[ToolReceipt] = field(default_factory=list)
    blocking_facts: list[BlockingFact] = field(default_factory=list)
    captured_at: float = field(default_factory=time.monotonic)

    def to_dict(self) -> dict[str, Any]:
        return {
            "files": {
                path: {
                    "category": fs.category.value,
                    "size_bytes": fs.size_bytes,
                    "change_type": fs.change_type,
                }
                for path, fs in self.files.items()
            },
            "receipts_count": len(self.receipts),
            "blocking_facts": [
                {
                    "description": bf.description,
                    "severity": bf.severity,
                    "related_files": bf.related_files,
                    "suggestion": bf.suggestion,
                }
                for bf in self.blocking_facts
            ],
            "captured_at": self.captured_at,
        }


class RuntimeStateCapsule:
    """Manages workspace state for coding tasks.

    Reference: OpenSquilla RuntimeStateCapsule — workspace diff tracking,
    mutation receipts, and blocking fact detection.
    """

    SOURCE_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".c", ".cpp", ".h"}
    TEST_PATTERNS = {"test_", "_test", ".test.", ".spec.", "/tests/", "/test/"}
    SCRATCH_PATTERNS = {"/tmp/", "temp_", "scratch", ".tmp"}
    CONFIG_EXTENSIONS = {".json", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".xml"}

    def __init__(self, workdir: str | None = None) -> None:
        self._workdir = workdir or os.getcwd()
        self._files: dict[str, FileState] = {}
        self._receipts: list[ToolReceipt] = []
        self._snapshots: list[WorkspaceSnapshot] = []

    def capture(self) -> WorkspaceSnapshot:
        """Capture current workspace state.

        Scans for dirty files (via git status if available, else filesystem),
        classifies them, and detects blocking facts.
        """
        files = self._scan_files()
        blocking_facts = self._detect_blocking_facts(files)

        snapshot = WorkspaceSnapshot(
            files=files,
            receipts=list(self._receipts[-50:]),  # Keep last 50 receipts
            blocking_facts=blocking_facts,
        )
        self._snapshots.append(snapshot)
        return snapshot

    def add_receipt(self, receipt: ToolReceipt) -> None:
        """Record a tool execution receipt."""
        self._receipts.append(receipt)
        if len(self._receipts) > 200:
            self._receipts = self._receipts[-100:]

    def classify_file(self, path: str) -> FileCategory:
        """Classify a file path into a category."""
        basename = os.path.basename(path.lower())

        # Check scratch patterns
        for pattern in self.SCRATCH_PATTERNS:
            if pattern in path.lower():
                return FileCategory.SCRATCH

        # Check test patterns
        for pattern in self.TEST_PATTERNS:
            if pattern in basename or pattern in path.lower():
                return FileCategory.TEST

        # Check config extensions
        ext = os.path.splitext(path)[1].lower()
        if ext in self.CONFIG_EXTENSIONS:
            return FileCategory.CONFIG

        # Check source extensions
        if ext in self.SOURCE_EXTENSIONS:
            return FileCategory.SOURCE

        return FileCategory.UNKNOWN

    def get_files_by_category(self, category: FileCategory) -> list[FileState]:
        """Get all tracked files in a category."""
        return [f for f in self._files.values() if f.category == category]

    def get_blocking_facts(self) -> list[BlockingFact]:
        """Get current blocking facts."""
        if self._snapshots:
            return self._snapshots[-1].blocking_facts
        return []

    def _scan_files(self) -> dict[str, FileState]:
        """Scan workspace for dirty/modified files."""
        files: dict[str, FileState] = {}

        # Try git status first
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self._workdir,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if not line:
                        continue
                    status = line[:2]
                    path = line[3:].strip()
                    change_type = "modified"
                    if "??" in status:
                        change_type = "added"
                    elif "D" in status:
                        change_type = "deleted"

                    full_path = os.path.join(self._workdir, path)
                    size = 0
                    mtime = 0.0
                    if os.path.exists(full_path) and change_type != "deleted":
                        try:
                            stat = os.stat(full_path)
                            size = stat.st_size
                            mtime = stat.st_mtime
                        except OSError:
                            pass

                    files[path] = FileState(
                        path=path,
                        category=self.classify_file(path),
                        size_bytes=size,
                        modified_at=mtime,
                        change_type=change_type,
                    )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        self._files = files
        return files

    def _detect_blocking_facts(self, files: dict[str, FileState]) -> list[BlockingFact]:
        """Detect blocking facts from current file state."""
        facts: list[BlockingFact] = []

        source_files = [f for f in files.values() if f.category == FileCategory.SOURCE]
        test_files = [f for f in files.values() if f.category == FileCategory.TEST]
        scratch_files = [f for f in files.values() if f.category == FileCategory.SCRATCH]

        # Scratch files without source files — likely incomplete
        if scratch_files and not source_files:
            facts.append(BlockingFact(
                description=f"{len(scratch_files)} scratch file(s) present but no source changes",
                severity="warning",
                related_files=[f.path for f in scratch_files],
                suggestion="Review scratch files — they may contain unintegrated work",
            ))

        # Source changes without tests
        if source_files and not test_files:
            # Check if any source file looks like production code (not config/utils)
            prod_sources = [f for f in source_files if "util" not in f.path.lower() and "config" not in f.path.lower()]
            if len(prod_sources) > 2:
                facts.append(BlockingFact(
                    description=f"{len(prod_sources)} source file(s) modified but no test changes detected",
                    severity="info",
                    related_files=[f.path for f in prod_sources],
                    suggestion="Consider adding or updating tests for the modified source files",
                ))

        # Large number of modified files — might be too ambitious
        modified = [f for f in files.values() if f.change_type == "modified"]
        if len(modified) > 15:
            facts.append(BlockingFact(
                description=f"{len(modified)} files modified — large change set",
                severity="info",
                related_files=[f.path for f in modified[:10]],
                suggestion="Large change set detected — consider breaking into smaller PRs",
            ))

        return facts

    def get_stats(self) -> dict[str, Any]:
        """Get workspace state statistics."""
        if not self._files:
            self._scan_files()

        categories: dict[str, int] = {}
        for f in self._files.values():
            cat = f.category.value
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_files": len(self._files),
            "categories": categories,
            "receipts_count": len(self._receipts),
            "snapshots_count": len(self._snapshots),
            "blocking_facts_count": len(self.get_blocking_facts()),
        }
