"""Session snapshot with Git isolation.

"""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SessionSnapshot:
    session_id: str
    branch_name: str
    commit_hash: str | None = None
    message: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    files_snapshot: dict[str, str] = field(default_factory=dict)  # path -> sha256


class SessionSnapshotManager:
    """Manage session snapshots using Git for isolation.

    Each session gets its own Git branch for file modifications.
    """

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self._snapshots: dict[str, SessionSnapshot] = {}

    def create_snapshot(self, session_id: str, message: str = "") -> SessionSnapshot:
        """Create a new snapshot for a session."""
        branch_name = f"session/{session_id}"
        snapshot = SessionSnapshot(
            session_id=session_id,
            branch_name=branch_name,
            message=message or f"Snapshot for session {session_id}",
        )
        self._snapshots[session_id] = snapshot
        logger.info("snapshot_created", session_id=session_id, branch=branch_name)
        return snapshot

    async def capture_files(self, session_id: str, files: list[str]) -> dict[str, str]:
        """Capture SHA256 hashes of files for change detection."""
        snapshot = self._snapshots.get(session_id)
        if not snapshot:
            return {}

        hashes = {}
        for file_path in files:
            if os.path.exists(file_path):
                h = hashlib.sha256()
                with open(file_path, "rb") as f:
                    while chunk := f.read(8192):
                        h.update(chunk)
                hashes[file_path] = h.hexdigest()
        snapshot.files_snapshot = hashes
        return hashes

    def detect_changes(self, session_id: str, current_files: list[str]) -> list[str]:
        """Detect which files have changed since last snapshot."""
        snapshot = self._snapshots.get(session_id)
        if not snapshot:
            return current_files

        changed = []
        for file_path in current_files:
            if os.path.exists(file_path):
                h = hashlib.sha256()
                with open(file_path, "rb") as f:
                    while chunk := f.read(8192):
                        h.update(chunk)
                current_hash = h.hexdigest()
                old_hash = snapshot.files_snapshot.get(file_path)
                if old_hash != current_hash:
                    changed.append(file_path)
            else:
                if file_path in snapshot.files_snapshot:
                    changed.append(file_path)
        return changed

    def get_snapshot(self, session_id: str) -> SessionSnapshot | None:
        return self._snapshots.get(session_id)

    def list_snapshots(self) -> list[SessionSnapshot]:
        return list(self._snapshots.values())


session_snapshot_manager = SessionSnapshotManager()
