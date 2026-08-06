"""Incremental file indexing service using SHA256 + timestamp.

Only re-indexes files that have changed since the last index operation.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class FileIndexEntry:
    path: str
    content_hash: str
    size_bytes: int
    modified_at: datetime
    indexed_at: datetime
    chunk_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class FileIndexService:
    """Track and index files incrementally using SHA256 content hashing.

    """

    def __init__(self):
        self._index: dict[str, FileIndexEntry] = {}

    def compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def compute_file_hash(self, file_path: str) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    def needs_indexing(self, path: str, content: str | None = None) -> bool:
        if path not in self._index:
            return True
        entry = self._index[path]
        if content is not None:
            return self.compute_hash(content) != entry.content_hash
        if os.path.exists(path):
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
            return mtime > entry.modified_at
        return False

    def record_index(self, path: str, content_hash: str, size_bytes: int, chunk_count: int = 0, metadata: dict[str, Any] | None = None) -> None:
        self._index[path] = FileIndexEntry(
            path=path,
            content_hash=content_hash,
            size_bytes=size_bytes,
            modified_at=datetime.now(UTC),
            indexed_at=datetime.now(UTC),
            chunk_count=chunk_count,
            metadata=metadata or {},
        )

    def get_changed_files(self, files: list[dict[str, Any]]) -> list[dict[str, Any]]:
        changed = []
        for f in files:
            path = f.get("path", "")
            content = f.get("content")
            if self.needs_indexing(path, content):
                changed.append(f)
        return changed

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_indexed": len(self._index),
            "total_chunks": sum(e.chunk_count for e in self._index.values()),
            "total_bytes": sum(e.size_bytes for e in self._index.values()),
        }


file_index_service = FileIndexService()
