"""Checkpoint storage for agent sessions.

- LangGraph `checkpoint/` 检查点快照机制
- OpenCode `session/` Session 状态模型
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from app.storage import async_session


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
    pending_writes: list[dict[str, Any]] = field(default_factory=list)  # 待处理写入


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
        self._store[cid] = checkpoint
        self._parents[cid] = parent_id
        return cid

    async def get(self, _thread_id: str | None, checkpoint_id: str) -> CheckpointData | None:
        return self._store.get(checkpoint_id)

    async def get_latest(self, _thread_id: str | None, session_id: str, thread_id: str = "") -> tuple[CheckpointData, str] | None:
        candidates = [
            (cid, cp) for cid, cp in self._store.items()
            if cp.session_id == session_id
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[1].iteration)
        cid, cp = candidates[-1]
        return cp, cid

    async def list_for_session(self, _thread_id: str | None, session_id: str) -> list[str]:
        return [cid for cid, cp in self._store.items() if cp.session_id == session_id]

    async def delete_for_session(self, _thread_id: str | None, session_id: str) -> int:
        to_delete = [cid for cid, cp in self._store.items() if cp.session_id == session_id]
        for cid in to_delete:
            del self._store[cid]
            self._parents.pop(cid, None)
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
        from app.storage.database import CheckpointRecord
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        cid = checkpoint_id or f"cp-{int(time.time()*1000)}"
        metadata_payload = {**checkpoint.metadata, "parent_id": parent_id}
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
            record = (
                await db.execute(
                    __import__("sqlalchemy")
                    .select(CheckpointRecord)
                    .where(CheckpointRecord.session_id == session_id)
                    .order_by(CheckpointRecord.iteration.desc(), CheckpointRecord.created_at.desc())
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
            metadata.setdefault("pending_writes", [])
            for w in writes:
                metadata["pending_writes"].append(
                    {
                        "channel": w.channel,
                        "value": w.value,
                        "write_id": w.write_id,
                        "status": w.status,
                    }
                )
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

    def _to_checkpoint(self, record: "CheckpointRecord") -> CheckpointData:
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
        return CheckpointData(
            session_id=record.session_id,
            messages=messages,
            iteration=record.iteration,
            status=record.status,
            tool_results=tool_results,
            metadata=metadata,
            pending_writes=pending_writes,
        )
