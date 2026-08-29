"""Checkpoint storage for agent sessions.

- LangGraph `checkpoint/` 检查点快照机制
- OpenCode `session/` Session 状态模型
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from app.storage import async_session

logger = structlog.get_logger()


@dataclass
class CheckpointData:
    session_id: str
    messages: list[dict[str, Any]]
    iteration: int
    status: str
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # LangGraph-style enhancements
    channel_values: dict[str, Any] = field(default_factory=dict)        # 状态通道快照
    channel_versions: dict[str, int] = field(default_factory=dict)      # 通道版本号
    versions_seen: dict[str, dict[str, int]] = field(default_factory=dict)  # 节点见过的版本
    pending_writes: list[PendingWrite] = field(default_factory=list)  # 待处理写入


@dataclass
class PendingWrite:
    """A write that is pending commit to a checkpoint."""
    channel: str
    value: Any
    write_id: str
    status: str = "pending"  # pending / committed / rolled_back


class InMemoryCheckpointStore:
    """Simple in-memory checkpoint store with LangGraph-style enhancements."""

    def __init__(self):
        self._store: dict[str, CheckpointData] = {}
        self._parents: dict[str, str | None] = {}
        self._threads: dict[str, str] = {}
        self._save_order: dict[str, int] = {}
        self._save_sequence = 0
        self._pending_writes: dict[str, list[PendingWrite]] = {}

    async def save(
        self,
        _thread_id: str | None,
        checkpoint: CheckpointData,
        thread_id: str = "",
        checkpoint_id: str = "",
        parent_id: str | None = None,
    ) -> str:
        cid = checkpoint_id or f"cp-{int(time.time()*1000)}"
        checkpoint.metadata["thread_id"] = thread_id
        self._store[cid] = checkpoint
        self._parents[cid] = parent_id
        self._threads[cid] = thread_id
        self._save_sequence += 1
        self._save_order[cid] = self._save_sequence
        return cid

    async def get(self, _thread_id: str | None, checkpoint_id: str) -> CheckpointData | None:
        return self._store.get(checkpoint_id)

    async def get_latest(self, _thread_id: str | None, session_id: str, thread_id: str = "") -> tuple[CheckpointData, str] | None:
        candidates = [
            (cid, cp) for cid, cp in self._store.items()
            if cp.session_id == session_id
            and (not thread_id or self._threads.get(cid) == thread_id)
        ]
        if not candidates:
            return None
        if thread_id:
            candidates.sort(key=lambda item: item[1].iteration)
        else:
            candidates.sort(key=lambda item: self._save_order[item[0]])
        cid, cp = candidates[-1]
        return cp, cid

    async def list_for_session(self, _thread_id: str | None, session_id: str) -> list[str]:
        return [cid for cid, cp in self._store.items() if cp.session_id == session_id]

    async def delete_for_session(self, _thread_id: str | None, session_id: str) -> int:
        to_delete = [cid for cid, cp in self._store.items() if cp.session_id == session_id]
        for cid in to_delete:
            del self._store[cid]
            self._parents.pop(cid, None)
            self._threads.pop(cid, None)
            self._save_order.pop(cid, None)
            self._pending_writes.pop(cid, None)
        return len(to_delete)

    async def put_writes(self, checkpoint_id: str, writes: list[PendingWrite]) -> None:
        """Persist pending writes for a checkpoint."""
        self._pending_writes.setdefault(checkpoint_id, []).extend(writes)

    async def get_writes(self, checkpoint_id: str) -> list[PendingWrite]:
        """Get pending writes for a checkpoint."""
        return self._pending_writes.get(checkpoint_id, [])


class SQLiteCheckpointStore:
    """Persistent checkpoint store backed by SQLite via SQLAlchemy.

    Replaces the default InMemoryCheckpointStore so checkpoints survive
    service restarts and can be shared across workers.
    """

    async def save(
        self,
        _thread_id: str | None,
        checkpoint: CheckpointData,
        thread_id: str = "",
        checkpoint_id: str = "",
        parent_id: str | None = None,
    ) -> str:
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        from app.storage.database import CheckpointRecord
        cid = checkpoint_id or f"cp-{int(time.time()*1000)}"
        saved_at = datetime.now(UTC).replace(tzinfo=None)
        metadata_payload = {
            **checkpoint.metadata,
            "parent_id": parent_id,
            "thread_id": thread_id,
        }
        metadata_payload["channel_values"] = checkpoint.channel_values
        metadata_payload["channel_versions"] = checkpoint.channel_versions
        metadata_payload["versions_seen"] = checkpoint.versions_seen
        metadata_payload["pending_writes"] = [
            {
                "channel": w.channel,
                "value": w.value,
                "write_id": w.write_id,
                "status": w.status,
            }
            for w in checkpoint.pending_writes
        ]
        async with async_session() as db:
            stmt = sqlite_insert(CheckpointRecord).values(
                id=cid,
                session_id=checkpoint.session_id,
                thread_id=thread_id or "",
                messages=json.dumps(checkpoint.messages, ensure_ascii=False),
                iteration=checkpoint.iteration,
                status=checkpoint.status,
                tool_results=json.dumps(checkpoint.tool_results, ensure_ascii=False),
                metadata_=json.dumps(metadata_payload, ensure_ascii=False),
                parent_id=parent_id,
                created_at=saved_at,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "session_id": checkpoint.session_id,
                    "thread_id": thread_id or "",
                    "messages": json.dumps(checkpoint.messages, ensure_ascii=False),
                    "iteration": checkpoint.iteration,
                    "status": checkpoint.status,
                    "tool_results": json.dumps(checkpoint.tool_results, ensure_ascii=False),
                    "metadata": json.dumps(metadata_payload, ensure_ascii=False),
                    "parent_id": parent_id,
                    "created_at": saved_at,
                },
            )
            await db.execute(stmt)
            await db.commit()
        return cid

    async def get(self, _thread_id: str | None, checkpoint_id: str) -> CheckpointData | None:
        from app.storage.database import CheckpointRecord
        async with async_session() as db:
            record = (
                await db.execute(
                    __import__("sqlalchemy").select(CheckpointRecord).where(CheckpointRecord.id == checkpoint_id)
                )
            ).scalar_one_or_none()
            if record is None:
                return None
            return self._to_checkpoint(record)

    async def load(self, session_id: str, turn_id: str) -> CheckpointData | None:
        """Retrieve a checkpoint by session_id + turn_id (thread_id)."""
        from app.storage.database import CheckpointRecord
        async with async_session() as db:
            record = (
                await db.execute(
                    __import__("sqlalchemy")
                    .select(CheckpointRecord)
                    .where(CheckpointRecord.session_id == session_id)
                    .where(CheckpointRecord.thread_id == turn_id)
                    .order_by(CheckpointRecord.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if record is None:
                return None
            return self._to_checkpoint(record)

    async def get_latest(self, _thread_id: str | None, session_id: str, thread_id: str = "") -> tuple[CheckpointData, str] | None:
        from app.storage.database import CheckpointRecord
        async with async_session() as db:
            query = (
                __import__("sqlalchemy")
                .select(CheckpointRecord)
                .where(CheckpointRecord.session_id == session_id)
            )
            if thread_id:
                query = query.where(CheckpointRecord.thread_id == thread_id)
                ordering = (
                    CheckpointRecord.iteration.desc(),
                    CheckpointRecord.created_at.desc(),
                )
            else:
                ordering = (
                    CheckpointRecord.created_at.desc(),
                    CheckpointRecord.iteration.desc(),
                )
            record = (
                await db.execute(
                    query.order_by(*ordering)
                    .limit(1)
                )
            ).scalar_one_or_none()
            if record is None:
                return None
            cp = self._to_checkpoint(record)
            return cp, record.id

    async def list_for_session(self, _thread_id: str | None, session_id: str) -> list[str]:
        from app.storage.database import CheckpointRecord
        async with async_session() as db:
            rows = (
                await db.execute(
                    __import__("sqlalchemy")
                    .select(CheckpointRecord.id)
                    .where(CheckpointRecord.session_id == session_id)
                    .order_by(CheckpointRecord.created_at.asc())
                )
            ).scalars().all()
            return list(rows)

    async def list(self, session_id: str) -> list[CheckpointData]:
        """Return all checkpoints for a session as CheckpointData objects."""
        from app.storage.database import CheckpointRecord
        async with async_session() as db:
            rows = (
                await db.execute(
                    __import__("sqlalchemy")
                    .select(CheckpointRecord)
                    .where(CheckpointRecord.session_id == session_id)
                    .order_by(CheckpointRecord.created_at.asc())
                )
            ).scalars().all()
            return [self._to_checkpoint(r) for r in rows]

    async def delete_for_session(self, _thread_id: str | None, session_id: str) -> int:
        from app.storage.database import CheckpointRecord
        async with async_session() as db:
            rows = (
                await db.execute(
                    __import__("sqlalchemy")
                    .select(CheckpointRecord.id)
                    .where(CheckpointRecord.session_id == session_id)
                )
            ).scalars().all()
            ids = list(rows)
            if ids:
                await db.execute(
                    __import__("sqlalchemy").delete(CheckpointRecord).where(CheckpointRecord.session_id == session_id)
                )
                await db.commit()
            return len(ids)

    async def delete(self, checkpoint_id: str) -> bool:
        """Remove a single checkpoint by id."""
        from app.storage.database import CheckpointRecord
        async with async_session() as db:
            result = await db.execute(
                __import__("sqlalchemy").delete(CheckpointRecord).where(CheckpointRecord.id == checkpoint_id)
            )
            await db.commit()
            return result.rowcount > 0

    async def put_writes(self, checkpoint_id: str, writes: list[PendingWrite]) -> None:
        from app.storage.database import CheckpointRecord
        metadata: dict[str, Any] = {}
        async with async_session() as db:
            record = (
                await db.execute(
                    __import__("sqlalchemy").select(CheckpointRecord).where(CheckpointRecord.id == checkpoint_id)
                )
            ).scalar_one_or_none()
            if record is None:
                return
            try:
                metadata = json.loads(record.metadata_ or "{}")
            except Exception:
                metadata = {}
            existing_raw = metadata.get("pending_writes", [])
            existing_writes: list[PendingWrite] = []
            for item in existing_raw:
                try:
                    existing_writes.append(PendingWrite(**item))
                except Exception:
                    logger.warning("checkpoint.invalid_pending_write", item=item)
                    continue
            existing_ids = {w.write_id for w in existing_writes}
            for w in writes:
                if w.write_id in existing_ids:
                    continue
                existing_writes.append(w)
                existing_ids.add(w.write_id)
            metadata["pending_writes"] = [
                {
                    "channel": w.channel,
                    "value": w.value,
                    "write_id": w.write_id,
                    "status": w.status,
                }
                for w in existing_writes
            ]
            record.metadata_ = json.dumps(metadata, ensure_ascii=False)
            await db.commit()

    async def get_writes(self, checkpoint_id: str) -> list[PendingWrite]:
        from app.storage.database import CheckpointRecord
        async with async_session() as db:
            record = (
                await db.execute(
                    __import__("sqlalchemy").select(CheckpointRecord).where(CheckpointRecord.id == checkpoint_id)
                )
            ).scalar_one_or_none()
            if record is None:
                return []
            try:
                metadata = json.loads(record.metadata_ or "{}")
            except Exception:
                return []
            raw = metadata.get("pending_writes", [])
            return [PendingWrite(**item) for item in raw]

    def _to_checkpoint(self, record: Any) -> CheckpointData:
        try:
            messages = json.loads(record.messages or "[]")
        except Exception:
            messages = []
        try:
            tool_results = json.loads(record.tool_results or "[]")
        except Exception:
            tool_results = []
        try:
            metadata = json.loads(record.metadata_ or "{}")
        except Exception:
            metadata = {}
        pending_writes_raw = metadata.pop("pending_writes", [])
        try:
            pending_writes = [PendingWrite(**item) for item in pending_writes_raw]
        except Exception:
            pending_writes = []
        channel_values = metadata.pop("channel_values", {}) or {}
        channel_versions = metadata.pop("channel_versions", {}) or {}
        versions_seen = metadata.pop("versions_seen", {}) or {}
        if not isinstance(channel_values, dict):
            channel_values = {}
        if not isinstance(channel_versions, dict):
            channel_versions = {}
        if not isinstance(versions_seen, dict):
            versions_seen = {}
        return CheckpointData(
            session_id=record.session_id,
            messages=messages,
            iteration=record.iteration,
            status=record.status,
            tool_results=tool_results,
            metadata=metadata,
            channel_values=channel_values,
            channel_versions=channel_versions,
            versions_seen=versions_seen,
            pending_writes=pending_writes,
        )
