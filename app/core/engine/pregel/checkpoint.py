"""Checkpoint persistence for Pregel execution.

Checkpoints capture the full state at super-step boundaries, enabling:
- Resume from failure after crashes
- Time-travel debugging
- Human-in-the-loop pause/resume
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import time
import uuid
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


def _generate_checkpoint_id() -> str:
    """Generate a lexicographically sortable checkpoint ID."""
    return f"cp-{uuid.uuid4().hex[:24]}-{int(time.time() * 1000):014d}"


class Checkpoint(BaseModel):
    """State snapshot at a super-step boundary.

    Attributes:
        id: Unique, lexicographically sortable checkpoint ID.
        values: Full state values at this point.
        next_nodes: List of pending node names to execute.
        parent_id: ID of the parent checkpoint (previous super-step).
        step: Super-step number this checkpoint represents.
        metadata: Additional metadata (thread_id, source, etc.).
        created_at: When this checkpoint was created.
    """

    id: str = Field(default_factory=_generate_checkpoint_id)
    values: dict[str, Any] = Field(default_factory=dict)
    next_nodes: list[str] = Field(default_factory=list)
    parent_id: str | None = None
    step: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "values": self.values,
            "next_nodes": self.next_nodes,
            "parent_id": self.parent_id,
            "step": self.step,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


class CheckpointConfig:
    """Configuration for checkpoint retrieval.

    Attributes:
        thread_id: The thread/session identifier.
        checkpoint_id: Specific checkpoint to retrieve (None = latest).
    """

    def __init__(self, thread_id: str = "default", checkpoint_id: str | None = None) -> None:
        self.thread_id = thread_id
        self.checkpoint_id = checkpoint_id


@runtime_checkable
class BaseCheckpointSaver(Protocol):
    """Protocol for checkpoint persistence backends."""

    async def put(self, config: CheckpointConfig, checkpoint: Checkpoint) -> CheckpointConfig:
        """Save a checkpoint and return updated config."""
        ...

    async def get(self, config: CheckpointConfig) -> Checkpoint | None:
        """Retrieve a checkpoint by config. Returns None if not found."""
        ...

    async def list(
        self,
        config: CheckpointConfig,
        *,
        limit: int = 10,
        before: str | None = None,
    ) -> list[Checkpoint]:
        """List checkpoints for a thread, newest first."""
        ...


class InMemoryCheckpointSaver:
    """In-memory checkpoint store (non-persistent, for testing/dev)."""

    def __init__(self) -> None:
        self._checkpoints: dict[str, Checkpoint] = {}
        self._thread_index: dict[str, list[str]] = {}
        self._lock = asyncio.Lock()

    async def put(self, config: CheckpointConfig, checkpoint: Checkpoint) -> CheckpointConfig:
        async with self._lock:
            self._checkpoints[checkpoint.id] = checkpoint
            self._thread_index.setdefault(config.thread_id, []).append(checkpoint.id)
            logger.debug(
                "checkpoint_saved",
                checkpoint_id=checkpoint.id,
                thread_id=config.thread_id,
                step=checkpoint.step,
            )
        return CheckpointConfig(
            thread_id=config.thread_id,
            checkpoint_id=checkpoint.id,
        )

    async def get(self, config: CheckpointConfig) -> Checkpoint | None:
        if config.checkpoint_id:
            if config.checkpoint_id not in self._thread_index.get(config.thread_id, []):
                return None
            return self._checkpoints.get(config.checkpoint_id)
        thread_cps = self._thread_index.get(config.thread_id, [])
        if not thread_cps:
            return None
        return self._checkpoints.get(thread_cps[-1])

    async def list(
        self,
        config: CheckpointConfig,
        *,
        limit: int = 10,
        before: str | None = None,
    ) -> list[Checkpoint]:
        thread_cps = self._thread_index.get(config.thread_id, [])
        if before:
            try:
                thread_cps = thread_cps[:thread_cps.index(before)]
            except ValueError:
                return []
        checkpoints = [
            self._checkpoints[cid]
            for cid in reversed(thread_cps)
            if cid in self._checkpoints
        ]
        return checkpoints[:limit]

    async def delete_thread(self, thread_id: str) -> int:
        """Delete all checkpoints for a thread."""
        async with self._lock:
            cids = self._thread_index.pop(thread_id, [])
            for cid in cids:
                self._checkpoints.pop(cid, None)
            return len(cids)


class SqliteCheckpointSaver:
    """SQLite-backed checkpoint saver (persistent)."""

    def __init__(self, db_path: str = "./checkpoints.db") -> None:
        self._db_path = db_path
        self._lock = asyncio.Lock()
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    step INTEGER NOT NULL,
                    values_json TEXT NOT NULL,
                    next_nodes_json TEXT NOT NULL DEFAULT '[]',
                    parent_id TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_checkpoints_thread_step
                ON checkpoints(thread_id, step DESC)
            """)
            conn.commit()

    async def put(self, config: CheckpointConfig, checkpoint: Checkpoint) -> CheckpointConfig:
        async with self._lock:
            await asyncio.to_thread(self._put_sync, config, checkpoint)
        return CheckpointConfig(
            thread_id=config.thread_id,
            checkpoint_id=checkpoint.id,
        )

    def _put_sync(self, config: CheckpointConfig, checkpoint: Checkpoint) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO checkpoints
                (id, thread_id, step, values_json, next_nodes_json, parent_id, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    checkpoint.id,
                    config.thread_id,
                    checkpoint.step,
                    json.dumps(checkpoint.values, default=str),
                    json.dumps(checkpoint.next_nodes),
                    checkpoint.parent_id,
                    json.dumps(checkpoint.metadata, default=str),
                    checkpoint.created_at.isoformat(),
                ),
            )
            conn.commit()
        logger.debug(
            "checkpoint_saved_sqlite",
            checkpoint_id=checkpoint.id,
            thread_id=config.thread_id,
            step=checkpoint.step,
        )

    async def get(self, config: CheckpointConfig) -> Checkpoint | None:
        return await asyncio.to_thread(self._get_sync, config)

    def _get_sync(self, config: CheckpointConfig) -> Checkpoint | None:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            if config.checkpoint_id:
                row = conn.execute(
                    "SELECT * FROM checkpoints WHERE id = ? AND thread_id = ?",
                    (config.checkpoint_id, config.thread_id),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM checkpoints WHERE thread_id = ? ORDER BY step DESC LIMIT 1",
                    (config.thread_id,),
                ).fetchone()
            if row:
                return self._row_to_checkpoint(row)
        return None

    async def list(
        self,
        config: CheckpointConfig,
        *,
        limit: int = 10,
        before: str | None = None,
    ) -> list[Checkpoint]:
        return await asyncio.to_thread(self._list_sync, config, limit, before)

    def _list_sync(
        self,
        config: CheckpointConfig,
        limit: int,
        before: str | None,
    ) -> list[Checkpoint]:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            if before:
                rows = conn.execute(
                    """
                    SELECT * FROM checkpoints
                    WHERE thread_id = ? AND rowid < (
                        SELECT rowid FROM checkpoints
                        WHERE id = ? AND thread_id = ?
                    )
                    ORDER BY rowid DESC LIMIT ?
                    """,
                    (config.thread_id, before, config.thread_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM checkpoints
                    WHERE thread_id = ?
                    ORDER BY rowid DESC LIMIT ?
                    """,
                    (config.thread_id, limit),
                ).fetchall()
            return [self._row_to_checkpoint(row) for row in rows]

    @staticmethod
    def _row_to_checkpoint(row: sqlite3.Row) -> Checkpoint:
        return Checkpoint(
            id=row["id"],
            values=json.loads(row["values_json"]),
            next_nodes=json.loads(row["next_nodes_json"]),
            parent_id=row["parent_id"],
            step=row["step"],
            metadata=json.loads(row["metadata_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    async def delete_thread(self, thread_id: str) -> int:
        """Delete all checkpoints for a thread."""
        async with self._lock:
            return await asyncio.to_thread(self._delete_thread_sync, thread_id)

    def _delete_thread_sync(self, thread_id: str) -> int:
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM checkpoints WHERE thread_id = ?",
                (thread_id,),
            )
            conn.commit()
            return cursor.rowcount
