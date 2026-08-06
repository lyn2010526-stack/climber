"""File System Isolation.

Provides path traversal prevention, symlink resolution,
file type allowlist, and temp directory management.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import structlog

logger = structlog.get_logger()


@dataclass
class FSIsolationConfig:
    """File system isolation configuration."""
    allowed_paths: list[str] = field(default_factory=list)
    blocked_paths: list[str] = field(default_factory=lambda: [
        "/etc/shadow", "/etc/passwd", "/etc/sudoers",
        "/root/.ssh", "/home/*/.ssh",
        "/proc", "/sys", "/dev",
    ])
    read_only_paths: list[str] = field(default_factory=list)
    temp_dir: str = ""
    max_file_size_mb: int = 50
    allowed_extensions: list[str] = field(default_factory=lambda: [
        ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml",
        ".md", ".txt", ".csv", ".html", ".css", ".xml", ".toml",
        ".sh", ".bash", ".sql", ".log", ".ini", ".cfg",
    ])


class FSIsolationManager:
    """Manages file system isolation policies."""

    PATH_TRAVERSAL_PATTERN = re.compile(r"\.\.[\\/]")
    SYMLINK_RESOLVE_MAX_DEPTH = 10

    def __init__(self, config: FSIsolationConfig | None = None):
        self.config = config or FSIsolationConfig()
        self._temp_dirs: list[str] = []

    def validate_path(self, path: str) -> tuple[bool, str]:
        """Validate path against isolation rules. Returns (ok, reason)."""
        if not path:
            return False, "Empty path"

        try:
            abs_path = Path(path).resolve()
        except (OSError, ValueError) as e:
            return False, f"Invalid path: {e}"

        if self._is_blocked(abs_path):
            return False, f"Path is blocked: {abs_path}"

        if self.config.allowed_paths and not self._is_allowed(abs_path):
            return False, f"Path outside allowed directories: {abs_path}"

        return True, ""

    def sanitize_path(self, path: str) -> str:
        """Sanitize a path, resolving traversal and symlinks."""
        if not path:
            raise ValueError("Empty path")

        resolved = Path(path).resolve()

        if self._contains_traversal(path):
            raise ValueError(f"Path traversal detected: {path}")

        if resolved.is_symlink():
            resolved = self._safe_resolve_symlink(resolved)

        return str(resolved)

    def create_temp(self, prefix: str = "fs_iso_") -> str:
        """Create a temporary directory within allowed paths."""
        if self.config.temp_dir:
            tmp = tempfile.mkdtemp(prefix=prefix, dir=self.config.temp_dir)
        else:
            tmp = tempfile.mkdtemp(prefix=prefix)
        self._temp_dirs.append(tmp)
        return tmp

    def cleanup_temp(self, temp_path: str | None = None) -> None:
        """Remove temporary directory/directories."""
        if temp_path:
            if temp_path in self._temp_dirs:
                self._temp_dirs.remove(temp_path)
            if os.path.isdir(temp_path):
                shutil.rmtree(temp_path, ignore_errors=True)
        else:
            for tmp in self._temp_dirs:
                if os.path.isdir(tmp):
                    shutil.rmtree(tmp, ignore_errors=True)
            self._temp_dirs.clear()

    def is_read_only(self, path: str) -> bool:
        """Check if path is in read-only list."""
        try:
            abs_path = Path(path).resolve()
        except (OSError, ValueError):
            return False

        for ro_path in self.config.read_only_paths:
            ro_abs = Path(ro_path).resolve()
            if str(abs_path) == str(ro_abs) or str(abs_path).startswith(str(ro_abs) + "/"):
                return True
        return False

    def validate_file_type(self, path: str) -> tuple[bool, str]:
        """Check if file extension is in allowlist."""
        ext = Path(path).suffix.lower()
        if not self.config.allowed_extensions:
            return True, ""
        if ext not in self.config.allowed_extensions:
            return False, f"File type '{ext}' not allowed. Allowed: {self.config.allowed_extensions}"
        return True, ""

    def validate_file_size(self, path: str) -> tuple[bool, str]:
        """Check if file size is within limit."""
        if not os.path.exists(path):
            return True, ""
        size_mb = os.path.getsize(path) / (1024 * 1024)
        if size_mb > self.config.max_file_size_mb:
            return False, f"File too large: {size_mb:.1f}MB (max {self.config.max_file_size_mb}MB)"
        return True, ""

    def _is_blocked(self, abs_path: Path) -> bool:
        """Check if path is in blocked list."""
        import fnmatch
        for blocked in self.config.blocked_paths:
            if "*" in blocked:
                if fnmatch.fnmatch(str(abs_path), blocked):
                    return True
                prefix = blocked.split("*")[0]
                if str(abs_path).startswith(prefix):
                    return True
            elif str(abs_path) == blocked or str(abs_path).startswith(blocked + "/"):
                return True
        return False

    def _is_allowed(self, abs_path: Path) -> bool:
        """Check if path is within allowed directories."""
        for allowed in self.config.allowed_paths:
            try:
                allowed_abs = Path(allowed).resolve()
                if str(abs_path) == str(allowed_abs) or str(abs_path).startswith(str(allowed_abs) + "/"):
                    return True
            except (OSError, ValueError):
                continue
        return False

    def _contains_traversal(self, path: str) -> bool:
        """Detect path traversal attempts."""
        return bool(self.PATH_TRAVERSAL_PATTERN.search(path))

    def _safe_resolve_symlink(self, path: Path) -> Path:
        """Resolve symlink with depth limit and blocked-path check."""
        current = path
        for _ in range(self.SYMLINK_RESOLVE_MAX_DEPTH):
            if not current.is_symlink():
                break
            target = os.readlink(str(current))
            if not os.path.isabs(target):
                target = str(current.parent / target)
            current = Path(target).resolve()
            if self._is_blocked(current):
                raise ValueError(f"Symlink target is blocked: {current}")
        return current
