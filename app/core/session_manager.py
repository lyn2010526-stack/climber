# app/core/session_manager.py
"""Session persistence manager — save, resume, and fork sessions.

Sessions are stored locally with full checkpoint history. Supports:
- Checkpoint save after each turn
- Resume from last checkpoint (crash recovery)
- Fork from any historical checkpoint (conversation branching)
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages session persistence with checkpoint/resume/fork capabilities."""

    def __init__(self, storage_dir: str = "./sessions"):
        self._storage = Path(storage_dir).resolve()
        self._storage.mkdir(parents=True, exist_ok=True)

    def _session_dir(self, session_id: str) -> Path:
        """Return a session directory constrained to the storage root."""
        if not session_id or session_id in {".", ".."} or Path(session_id).name != session_id:
            raise ValueError("Invalid session id")
        session_dir = (self._storage / session_id).resolve()
        try:
            session_dir.relative_to(self._storage)
        except ValueError:
            raise ValueError("Invalid session id") from None
        return session_dir

    def save_checkpoint(
        self,
        session_id: str,
        messages: list[dict],
        iteration: int,
        status: str = "active",
        metadata: dict | None = None,
    ):
        """Save a checkpoint for a session."""
        checkpoint = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "messages": messages,
            "iteration": iteration,
            "status": status,
            "metadata": metadata or {},
            "timestamp": time.time(),
        }
        session_dir = self._session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_file = session_dir / f"checkpoint_{iteration:04d}.json"
        checkpoint_file.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2))
        # Update latest symlink / pointer
        latest_link = session_dir / "latest.json"
        latest_link.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2))
        logger.debug("Saved checkpoint for session %s at iteration %d", session_id, iteration)

    def get_latest_checkpoint(self, session_id: str) -> dict | None:
        """Get the most recent checkpoint for a session."""
        latest_file = self._session_dir(session_id) / "latest.json"
        if latest_file.exists():
            return json.loads(latest_file.read_text())
        return None

    def get_checkpoint_history(self, session_id: str) -> list[dict]:
        """Get all checkpoints for a session, ordered by iteration."""
        session_dir = self._session_dir(session_id)
        if not session_dir.exists():
            return []
        checkpoints = []
        for f in sorted(session_dir.glob("checkpoint_*.json")):
            checkpoints.append(json.loads(f.read_text()))
        return checkpoints

    def resume_session(self, session_id: str) -> dict | None:
        """Resume a session from its latest checkpoint."""
        checkpoint = self.get_latest_checkpoint(session_id)
        if checkpoint is None:
            return None
        logger.info("Resuming session %s from iteration %d", session_id, checkpoint["iteration"])
        return checkpoint

    def fork_session(self, source_session_id: str, new_session_id: str | None = None) -> str:
        """Fork a session from its latest checkpoint (conversation branching)."""
        source = self.get_latest_checkpoint(source_session_id)
        if source is None:
            raise ValueError(f"Session '{source_session_id}' not found")

        new_id = new_session_id or f"{source_session_id}-fork-{uuid.uuid4().hex[:8]}"
        forked = dict(source)
        forked["session_id"] = new_id
        forked["parent_session"] = source_session_id
        forked["id"] = str(uuid.uuid4())
        forked["timestamp"] = time.time()

        session_dir = self._session_dir(new_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_file = session_dir / "checkpoint_0000.json"
        checkpoint_file.write_text(json.dumps(forked, ensure_ascii=False, indent=2))
        latest_link = session_dir / "latest.json"
        latest_link.write_text(json.dumps(forked, ensure_ascii=False, indent=2))
        logger.info("Forked session %s -> %s", source_session_id, new_id)
        return new_id

    def list_sessions(self) -> list[dict]:
        """List all saved sessions with their latest state."""
        sessions = []
        for session_dir in sorted(self._storage.iterdir()):
            if session_dir.is_dir():
                latest = session_dir / "latest.json"
                if latest.exists():
                    data = json.loads(latest.read_text())
                    sessions.append({
                        "session_id": data.get("session_id", session_dir.name),
                        "iteration": data.get("iteration", 0),
                        "status": data.get("status", "unknown"),
                        "timestamp": data.get("timestamp", 0),
                    })
        return sessions

    def delete_session(self, session_id: str) -> bool:
        """Delete all checkpoints for a session."""
        import shutil
        session_dir = self._session_dir(session_id)
        if session_dir.exists():
            shutil.rmtree(session_dir)
            return True
        return False
