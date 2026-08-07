"""File handling and manipulation tools."""

from __future__ import annotations

import hashlib
import mimetypes
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

import structlog

from app.tools import ToolRegistry

logger = structlog.get_logger()

WORKSPACE_DIR = Path(os.environ.get("AGENT_WORKSPACE", "./workspace"))
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".json", ".yaml", ".yml", ".csv", ".tsv",
    ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css",
    ".xml", ".toml", ".ini", ".cfg", ".conf", ".log",
    ".sql", ".sh", ".bash", ".zsh", ".env",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
}


class FileTools:
    """Comprehensive file operation tools."""

    def __init__(self, workspace: str | Path | None = None):
        self.workspace = Path(workspace) if workspace else WORKSPACE_DIR
        self.workspace.mkdir(parents=True, exist_ok=True)

    def register(self, registry: ToolRegistry) -> None:
        """Register all file tools."""
        registry.register(
            name="file_read",
            description="Read file contents with encoding detection",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to workspace"},
                    "encoding": {"type": "string", "description": "File encoding (default: utf-8)"},
                    "offset": {"type": "integer", "description": "Line offset to start reading"},
                    "limit": {"type": "integer", "description": "Maximum lines to read"},
                },
                "required": ["path"],
            },
            func=self.read_file,
        )
        registry.register(
            name="file_write",
            description="Write content to a file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to workspace"},
                    "content": {"type": "string", "description": "Content to write"},
                    "encoding": {"type": "string", "description": "File encoding (default: utf-8)"},
                    "append": {"type": "boolean", "description": "Append instead of overwrite"},
                },
                "required": ["path", "content"],
            },
            func=self.write_file,
        )
        registry.register(
            name="file_delete",
            description="Delete a file or directory",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to delete"},
                    "recursive": {"type": "boolean", "description": "Delete directories recursively"},
                },
                "required": ["path"],
            },
            func=self.delete_file,
        )
        registry.register(
            name="file_list",
            description="List files and directories",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path (default: workspace root)"},
                    "pattern": {"type": "string", "description": "Glob pattern to filter"},
                    "recursive": {"type": "boolean", "description": "List recursively"},
                    "include_hidden": {"type": "boolean", "description": "Include hidden files"},
                },
                "required": [],
            },
            func=self.list_files,
        )
        registry.register(
            name="file_copy",
            description="Copy a file or directory",
            parameters={
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source path"},
                    "destination": {"type": "string", "description": "Destination path"},
                    "overwrite": {"type": "boolean", "description": "Overwrite if exists"},
                },
                "required": ["source", "destination"],
            },
            func=self.copy_file,
        )
        registry.register(
            name="file_move",
            description="Move or rename a file or directory",
            parameters={
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source path"},
                    "destination": {"type": "string", "description": "Destination path"},
                },
                "required": ["source", "destination"],
            },
            func=self.move_file,
        )
        registry.register(
            name="file_info",
            description="Get file metadata and info",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                },
                "required": ["path"],
            },
            func=self.file_info,
        )
        registry.register(
            name="file_search",
            description="Search file contents by pattern",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search pattern (regex supported)"},
                    "path": {"type": "string", "description": "Directory to search in"},
                    "file_pattern": {"type": "string", "description": "File glob pattern"},
                    "max_results": {"type": "integer", "description": "Maximum results (default: 50)"},
                },
                "required": ["pattern"],
            },
            func=self.search_files,
        )
        registry.register(
            name="file_archive",
            description="Create or extract archive files",
            parameters={
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "description": "create or extract"},
                    "archive_path": {"type": "string", "description": "Archive file path"},
                    "source_paths": {"type": "array", "items": {"type": "string"}, "description": "Files to archive"},
                    "destination": {"type": "string", "description": "Extraction destination"},
                },
                "required": ["operation", "archive_path"],
            },
            func=self.archive_file,
        )

    def _resolve_path(self, path: str) -> Path:
        """Resolve path within workspace."""
        target = (self.workspace / path).resolve()
        if not str(target).startswith(str(self.workspace.resolve())):
            raise ValueError("Path traversal detected")
        return target

    def read_file(self, path: str, encoding: str = "utf-8", offset: int = 0, limit: int | None = None) -> dict:
        """Read file contents."""
        target = self._resolve_path(path)
        if not target.exists():
            return {"error": f"File not found: {path}"}
        if not target.is_file():
            return {"error": f"Not a file: {path}"}

        content = target.read_text(encoding=encoding, errors="replace")
        lines = content.split("\n")

        if offset or limit:
            lines = lines[offset:offset + limit] if limit else lines[offset:]

        return {
            "path": path,
            "content": "\n".join(lines),
            "total_lines": len(content.split("\n")),
            "size": target.stat().st_size,
            "encoding": encoding,
        }

    def write_file(self, path: str, content: str, encoding: str = "utf-8", append: bool = False) -> dict:
        """Write content to file."""
        target = self._resolve_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)

        if append and target.exists():
            existing = target.read_text(encoding=encoding, errors="replace")
            content = existing + content

        target.write_text(content, encoding=encoding)
        return {
            "path": path,
            "size": target.stat().st_size,
            "lines": len(content.split("\n")),
        }

    def delete_file(self, path: str, recursive: bool = False) -> dict:
        """Delete file or directory."""
        target = self._resolve_path(path)
        if not target.exists():
            return {"error": f"Path not found: {path}"}

        if target.is_dir():
            if recursive:
                shutil.rmtree(target)
            else:
                target.rmdir()
        else:
            target.unlink()

        return {"path": path, "deleted": True}

    def list_files(self, path: str = ".", pattern: str = "*", recursive: bool = False, include_hidden: bool = False) -> dict:
        """List files and directories."""
        target = self._resolve_path(path)
        if not target.exists():
            return {"error": f"Directory not found: {path}"}

        items = []
        glob_iter = target.rglob(pattern) if recursive else target.glob(pattern)

        for item in sorted(glob_iter):
            if not include_hidden and item.name.startswith("."):
                continue
            stat = item.stat()
            items.append({
                "name": item.name,
                "path": str(item.relative_to(self.workspace)),
                "type": "directory" if item.is_dir() else "file",
                "size": stat.st_size if item.is_file() else 0,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })

        return {"path": path, "items": items, "total": len(items)}

    def copy_file(self, source: str, destination: str, overwrite: bool = False) -> dict:
        """Copy file or directory."""
        src = self._resolve_path(source)
        dst = self._resolve_path(destination)

        if not src.exists():
            return {"error": f"Source not found: {source}"}
        if dst.exists() and not overwrite:
            return {"error": f"Destination exists: {destination}"}

        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=overwrite)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

        return {"source": source, "destination": destination, "copied": True}

    def move_file(self, source: str, destination: str) -> dict:
        """Move file or directory."""
        src = self._resolve_path(source)
        dst = self._resolve_path(destination)

        if not src.exists():
            return {"error": f"Source not found: {source}"}

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return {"source": source, "destination": destination, "moved": True}

    def file_info(self, path: str) -> dict:
        """Get file metadata."""
        target = self._resolve_path(path)
        if not target.exists():
            return {"error": f"File not found: {path}"}

        stat = target.stat()
        mime_type, _ = mimetypes.guess_type(str(target))
        info = {
            "path": path,
            "name": target.name,
            "type": "directory" if target.is_dir() else "file",
            "size": stat.st_size,
            "mime_type": mime_type or "application/octet-stream",
            "permissions": oct(stat.st_mode)[-3:],
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
        }

        if target.is_file():
            content = target.read_bytes()
            info["checksum_md5"] = hashlib.md5(content).hexdigest()
            info["checksum_sha256"] = hashlib.sha256(content).hexdigest()

        return info

    def search_files(self, pattern: str, path: str = ".", file_pattern: str = "*", max_results: int = 50) -> dict:
        """Search file contents."""
        import re
        target = self._resolve_path(path)
        if not target.exists():
            return {"error": f"Directory not found: {path}"}

        results = []
        regex = re.compile(pattern)

        for file_path in target.rglob(file_pattern):
            if file_path.is_dir():
                continue
            if file_path.stat().st_size > MAX_FILE_SIZE:
                continue
            try:
                content = file_path.read_text(errors="replace")
                for i, line in enumerate(content.split("\n"), 1):
                    if regex.search(line):
                        results.append({
                            "file": str(file_path.relative_to(self.workspace)),
                            "line": i,
                            "content": line.strip(),
                        })
                        if len(results) >= max_results:
                            break
            except (OSError, UnicodeDecodeError):
                continue
            if len(results) >= max_results:
                break

        return {"pattern": pattern, "results": results, "total": len(results)}

    def archive_file(self, operation: str, archive_path: str, source_paths: list[str] | None = None, destination: str | None = None) -> dict:
        """Create or extract archive."""
        archive = self._resolve_path(archive_path)

        if operation == "create":
            if not source_paths:
                return {"error": "No source paths provided"}
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
                for src in source_paths:
                    src_path = self._resolve_path(src)
                    if src_path.is_dir():
                        for f in src_path.rglob("*"):
                            if f.is_file():
                                zf.write(f, f.relative_to(src_path.parent))
                    elif src_path.is_file():
                        zf.write(src_path, src_path.name)
            return {"operation": "create", "archive": archive_path, "files": len(source_paths)}

        elif operation == "extract":
            dest = self._resolve_path(destination) if destination else self.workspace
            with zipfile.ZipFile(archive, "r") as zf:
                zf.extractall(dest)
            return {"operation": "extract", "archive": archive_path, "destination": destination or "."}

        return {"error": f"Unknown operation: {operation}"}
