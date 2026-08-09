"""MemFS Store — Git-backed memory file system for agents.

Provides CRUD operations on memory files with git versioning.
All writes are committed to git automatically, giving agents a
versioned, auditable memory store.

Memory directory structure:
    memfs/
    ├── system/           # Injected every turn (persona, human)
    │   ├── persona.md    # Agent identity, values, behavior rules
    │   └── human.md      # User preferences, project facts
    ├── reference/        # On-demand retrieval
    │   └── project-notes.md
    ├── skills/           # Agent skills (versioned, migratable)
    │   └── my-skill/SKILL.md
    └── conversations/    # Conversation history index
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from app.core.memfs.memory_block import MemoryBlock

logger = structlog.get_logger()

DEFAULT_SYSTEM_FILES: dict[str, dict[str, Any]] = {
    "system/persona.md": {
        "description": "Agent identity, values, and behavior rules",
        "importance": 1.0,
        "tags": ["system", "identity"],
    },
    "system/human.md": {
        "description": "User preferences and project facts",
        "importance": 1.0,
        "tags": ["system", "user"],
    },
    "reference/project-notes.md": {
        "description": "Project-level reference notes and documentation",
        "importance": 0.8,
        "tags": ["reference", "project"],
    },
    "conversations/_index.md": {
        "description": "Conversation history index",
        "importance": 0.5,
        "tags": ["conversations", "index"],
    },
}


class MemFS:
    """Git-backed memory file system for agents.

    All operations are async-compatible. File system operations run
    in a thread pool to avoid blocking the event loop. Git commits
    are performed synchronously but are lightweight.

    Args:
        base_path: Root directory for the memory filesystem.
        auto_commit: Whether to automatically git-commit changes.
    """

    def __init__(
        self,
        base_path: str,
        auto_commit: bool = True,
    ) -> None:
        self._base_path = Path(base_path).resolve()
        self._auto_commit = auto_commit
        self._base_path.mkdir(parents=True, exist_ok=True)
        self._git_available = self._check_git()
        self._lock = asyncio.Lock()

        if self._git_available:
            self._init_git()

    @property
    def base_path(self) -> Path:
        return self._base_path

    @property
    def git_enabled(self) -> bool:
        return self._git_available

    def _check_git(self) -> bool:
        """Check if git is available and the base_path is a git repo."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=str(self._base_path),
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _init_git(self) -> None:
        """Initialize git repo if not already initialized."""
        git_dir = self._base_path / ".git"
        if not git_dir.exists():
            try:
                subprocess.run(
                    ["git", "init"],
                    cwd=str(self._base_path),
                    capture_output=True,
                    timeout=10,
                )
                gitignore = self._base_path / ".gitignore"
                gitignore.write_text("__pycache__/\n*.pyc\n")
                subprocess.run(
                    ["git", "add", ".gitignore"],
                    cwd=str(self._base_path),
                    capture_output=True,
                    timeout=5,
                )
                subprocess.run(
                    ["git", "commit", "-m", "chore: initialize memfs", "--allow-empty"],
                    cwd=str(self._base_path),
                    capture_output=True,
                    timeout=5,
                )
                logger.info("memfs_git_initialized", path=str(self._base_path))
            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                logger.warning("memfs_git_init_failed", error=str(e))
                self._git_available = False

    async def read(self, path: str) -> str:
        """Read a memory file and return its content (without frontmatter).

        Args:
            path: Relative path within the memory filesystem.

        Returns:
            The file content as a string.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        async with self._lock:
            return await asyncio.to_thread(self._read_sync, path)

    def _read_sync(self, path: str) -> str:
        file_path = self._resolve_path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Memory file not found: {path}")

        raw = file_path.read_text(encoding="utf-8")
        try:
            block = MemoryBlock.from_markdown(path, raw)
            return block.content
        except Exception:
            return raw

    async def read_block(self, path: str) -> MemoryBlock:
        """Read a memory file and return it as a MemoryBlock with metadata.

        Args:
            path: Relative path within the memory filesystem.

        Returns:
            MemoryBlock with metadata and content.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        async with self._lock:
            return await asyncio.to_thread(self._read_block_sync, path)

    def _read_block_sync(self, path: str) -> MemoryBlock:
        file_path = self._resolve_path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Memory file not found: {path}")

        raw = file_path.read_text(encoding="utf-8")
        return MemoryBlock.from_markdown(path, raw)

    async def write(self, path: str, content: str) -> None:
        """Write content to a memory file.

        If the file already exists with frontmatter, preserves the metadata.
        Otherwise creates a new file with default metadata.

        Args:
            path: Relative path within the memory filesystem.
            content: The content to write.
        """
        async with self._lock:
            await asyncio.to_thread(self._write_sync, path, content)

    def _write_sync(self, path: str, content: str) -> None:
        file_path = self._resolve_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        existing_block = None
        if file_path.exists():
            try:
                raw = file_path.read_text(encoding="utf-8")
                existing_block = MemoryBlock.from_markdown(path, raw)
                existing_block.content = content
            except Exception:
                pass

        block = MemoryBlock.new(path=path, content=content) if existing_block is None else existing_block

        file_path.write_text(block.to_markdown(), encoding="utf-8")

        if self._auto_commit and self._git_available:
            self._git_commit_file(path, "update")

    async def write_block(self, block: MemoryBlock) -> None:
        """Write a MemoryBlock with full metadata control.

        Args:
            block: The MemoryBlock to persist.
        """
        async with self._lock:
            await asyncio.to_thread(self._write_block_sync, block)

    def _write_block_sync(self, block: MemoryBlock) -> None:
        file_path = self._resolve_path(block.path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(block.to_markdown(), encoding="utf-8")

        if self._auto_commit and self._git_available:
            self._git_commit_file(block.path, "update")

    async def append(self, path: str, content: str) -> None:
        """Append content to an existing memory file.

        Args:
            path: Relative path within the memory filesystem.
            content: The content to append.
        """
        async with self._lock:
            await asyncio.to_thread(self._append_sync, path, content)

    def _append_sync(self, path: str, content: str) -> None:
        file_path = self._resolve_path(path)

        if file_path.exists():
            try:
                raw = file_path.read_text(encoding="utf-8")
                block = MemoryBlock.from_markdown(path, raw)
                block.content = block.content.rstrip() + "\n" + content.strip() + "\n"
            except Exception:
                existing = file_path.read_text(encoding="utf-8")
                file_path.write_text(existing.rstrip() + "\n" + content.strip() + "\n", encoding="utf-8")
                if self._auto_commit and self._git_available:
                    self._git_commit_file(path, "append")
                return
        else:
            block = MemoryBlock.new(path=path, content=content)

        file_path.write_text(block.to_markdown(), encoding="utf-8")

        if self._auto_commit and self._git_available:
            self._git_commit_file(path, "append")

    async def list_files(self, prefix: str = "") -> list[str]:
        """List all memory files, optionally filtered by prefix.

        Args:
            prefix: Optional path prefix filter (e.g. "system/").

        Returns:
            List of relative paths (sorted).
        """
        async with self._lock:
            return await asyncio.to_thread(self._list_sync, prefix)

    def _list_sync(self, prefix: str = "") -> list[str]:
        results: list[str] = []

        search_dir = self._base_path
        if prefix:
            search_dir = self._resolve_path(prefix)

        if not search_dir.exists():
            return []

        if search_dir.is_file():
            rel = str(search_dir.relative_to(self._base_path))
            return [rel]

        for root, dirs, files in os.walk(str(search_dir)):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            for fname in files:
                if fname.startswith(".") and fname != ".gitignore":
                    continue
                full = Path(root) / fname
                rel = str(full.relative_to(self._base_path))
                results.append(rel)

        results.sort()
        return results

    async def delete(self, path: str) -> None:
        """Delete a memory file.

        Args:
            path: Relative path within the memory filesystem.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        async with self._lock:
            await asyncio.to_thread(self._delete_sync, path)

    def _delete_sync(self, path: str) -> None:
        file_path = self._resolve_path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Memory file not found: {path}")

        file_path.unlink()

        if self._auto_commit and self._git_available:
            self._git_remove_file(path)

    async def get_tree(self) -> dict[str, Any]:
        """Get the directory tree structure of the memory filesystem.

        Returns:
            Nested dict representing the directory structure.
        """
        async with self._lock:
            return await asyncio.to_thread(self._get_tree_sync)

    def _get_tree_sync(self) -> dict[str, Any]:
        return self._build_tree(self._base_path)

    def _build_tree(self, dir_path: Path) -> dict[str, Any]:
        """Recursively build a directory tree."""
        tree: dict[str, Any] = {"_files": [], "_dirs": {}}

        if not dir_path.exists():
            return tree

        try:
            entries = sorted(dir_path.iterdir())
        except PermissionError:
            return tree

        for entry in entries:
            if entry.name.startswith(".") and entry.name != ".gitignore":
                continue
            if entry.name == "__pycache__":
                continue

            if entry.is_dir():
                subtree = self._build_tree(entry)
                tree["_dirs"][entry.name] = subtree
            elif entry.is_file():
                rel = str(entry.relative_to(self._base_path))
                size = entry.stat().st_size
                mtime = datetime.fromtimestamp(
                    entry.stat().st_mtime, tz=UTC
                ).isoformat()
                tree["_files"].append({
                    "path": rel,
                    "size": size,
                    "modified": mtime,
                })

        return tree

    async def exists(self, path: str) -> bool:
        """Check if a memory file exists."""
        async with self._lock:
            return await asyncio.to_thread(self._exists_sync, path)

    def _exists_sync(self, path: str) -> bool:
        return self._resolve_path(path).exists()

    async def get_history(self, path: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get git history for a memory file.

        Args:
            path: Relative path within the memory filesystem.
            limit: Maximum number of history entries to return.

        Returns:
            List of dicts with commit hash, date, author, and message.
        """
        if not self._git_available:
            return []

        async with self._lock:
            return await asyncio.to_thread(self._get_history_sync, path, limit)

    def _get_history_sync(self, path: str, limit: int) -> list[dict[str, Any]]:
        try:
            result = subprocess.run(
                [
                    "git", "log", f"--max-count={limit}",
                    "--format=%H|%aI|%an|%s", "--", path,
                ],
                cwd=str(self._base_path),
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return []

            history: list[dict[str, Any]] = []
            for line in result.stdout.strip().splitlines():
                parts = line.split("|", 3)
                if len(parts) == 4:
                    history.append({
                        "hash": parts[0][:12],
                        "date": parts[1],
                        "author": parts[2],
                        "message": parts[3],
                    })
            return history
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

    async def search(self, query: str) -> list[dict[str, Any]]:
        """Search memory files by content (grep-based).

        Args:
            query: Search string (case-insensitive).

        Returns:
            List of dicts with path and matching lines.
        """
        async with self._lock:
            return await asyncio.to_thread(self._search_sync, query)

    def _search_sync(self, query: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        for root, dirs, files in os.walk(str(self._base_path)):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            for fname in files:
                if fname.startswith("."):
                    continue
                full = Path(root) / fname
                rel = str(full.relative_to(self._base_path))

                try:
                    content = full.read_text(encoding="utf-8")
                except (UnicodeDecodeError, PermissionError):
                    continue

                matches: list[str] = []
                for i, line in enumerate(content.splitlines(), 1):
                    if query.lower() in line.lower():
                        matches.append(f"L{i}: {line.strip()}")

                if matches:
                    results.append({
                        "path": rel,
                        "matches": matches[:10],
                        "total_matches": len(matches),
                    })

        return results

    async def init_defaults(self) -> list[str]:
        """Initialize default system memory files if they don't exist.

        Returns:
            List of paths that were created.
        """
        created: list[str] = []
        for path, meta in DEFAULT_SYSTEM_FILES.items():
            if not await self.exists(path):
                content = f"# {meta['description']}\n\n"
                block = MemoryBlock.new(
                    path=path,
                    content=content,
                    description=meta["description"],
                    importance=meta.get("importance", 0.5),
                    tags=meta.get("tags", []),
                )
                await self.write_block(block)
                created.append(path)

        if created:
            logger.info("memfs_defaults_initialized", created=created)

        return created

    def _resolve_path(self, path: str) -> Path:
        """Resolve a relative path to an absolute path, preventing traversal."""
        resolved = (self._base_path / path).resolve()
        if not str(resolved).startswith(str(self._base_path)):
            raise ValueError(f"Path traversal detected: {path}")
        return resolved

    def _git_commit_file(self, path: str, action: str) -> None:
        """Commit a file change to git."""
        try:
            subprocess.run(
                ["git", "add", path],
                cwd=str(self._base_path),
                capture_output=True,
                timeout=5,
            )
            subprocess.run(
                [
                    "git", "commit", "-m",
                    f"memfs: {action} {path}",
                    "--quiet",
                ],
                cwd=str(self._base_path),
                capture_output=True,
                timeout=5,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    def _git_remove_file(self, path: str) -> None:
        """Remove a file from git tracking."""
        try:
            subprocess.run(
                ["git", "rm", "--cached", path],
                cwd=str(self._base_path),
                capture_output=True,
                timeout=5,
            )
            subprocess.run(
                [
                    "git", "commit", "-m",
                    f"memfs: delete {path}",
                    "--quiet",
                ],
                cwd=str(self._base_path),
                capture_output=True,
                timeout=5,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
