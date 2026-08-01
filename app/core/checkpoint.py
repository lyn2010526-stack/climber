"""Checkpoint storage for agent sessions.

- LangGraph `checkpoint/` 检查点快照机制
- OpenCode `session/` Session 状态模型
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any


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
    """SQLite-backed checkpoint store with LangGraph-style enhancements."""

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path

    async def save(
        self,
        _thread_id: str | None,
        checkpoint: CheckpointData,
        thread_id: str = "",
        checkpoint_id: str = "",
        parent_id: str | None = None,
    ) -> str:
        from app.storage import async_session
        from app.storage.database import CheckpointRecord

        cid = checkpoint_id or f"cp-{int(time.time()*1000)}"
        record = CheckpointRecord(
            id=cid,
            session_id=checkpoint.session_id,
            thread_id=thread_id,
            messages=json.dumps(checkpoint.messages),
            iteration=checkpoint.iteration,
            status=checkpoint.status,
            tool_results=json.dumps(checkpoint.tool_results),
            metadata_=json.dumps(checkpoint.metadata),
            parent_id=parent_id,
        )
        async with async_session() as session:
            session.add(record)
            await session.commit()
        return cid

    async def get(self, _thread_id: str | None, checkpoint_id: str) -> CheckpointData | None:
        from app.storage import async_session
        from app.storage.database import CheckpointRecord
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(
                select(CheckpointRecord).where(CheckpointRecord.id == checkpoint_id)
            )
            record = result.scalar_one_or_none()
            if not record:
                return None
            return CheckpointData(
                session_id=record.session_id,
                messages=json.loads(record.messages),
                iteration=record.iteration,
                status=record.status,
                tool_results=json.loads(record.tool_results),
                metadata=json.loads(record.metadata_),
            )

    async def get_latest(self, _thread_id: str | None, session_id: str, thread_id: str = "") -> tuple[CheckpointData, str] | None:
        from app.storage import async_session
        from app.storage.database import CheckpointRecord
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(
                select(CheckpointRecord)
                .where(CheckpointRecord.session_id == session_id)
                .order_by(CheckpointRecord.iteration.desc())
                .limit(1)
            )
            record = result.scalar_one_or_none()
            if not record:
                return None
            checkpoint = CheckpointData(
                session_id=record.session_id,
                messages=json.loads(record.messages),
                iteration=record.iteration,
                status=record.status,
                tool_results=json.loads(record.tool_results),
                metadata=json.loads(record.metadata_),
            )
            return checkpoint, record.id

    async def list_for_session(self, _thread_id: str | None, session_id: str) -> list[str]:
        from app.storage import async_session
        from app.storage.database import CheckpointRecord
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(
                select(CheckpointRecord.id).where(CheckpointRecord.session_id == session_id)
            )
            return [row[0] for row in result.all()]

    async def delete_for_session(self, _thread_id: str | None, session_id: str) -> int:
        from app.storage import async_session
        from app.storage.database import CheckpointRecord
        from sqlalchemy import delete

        async with async_session() as session:
            result = await session.execute(
                delete(CheckpointRecord).where(CheckpointRecord.session_id == session_id)
            )
            await session.commit()
            return result.rowcount

    async def put_writes(self, checkpoint_id: str, writes: list[PendingWrite]) -> None:
        """Persist pending writes for a checkpoint."""
        pass

    async def get_writes(self, checkpoint_id: str) -> list[PendingWrite]:
        """Get pending writes for a checkpoint."""
        return []

    async def get_state_history(
        self,
        session_id: str,
        limit: int = 20,
    ) -> list[tuple[CheckpointData, str]]:
        """获取历史 checkpoint 列表 — 参考 LangGraph get_state_history

        LangGraph 返回 StateSnapshot(values, next, config, metadata, created_at, parent_config, tasks)
        """
        from app.storage import async_session
        from app.storage.database import CheckpointRecord
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(
                select(CheckpointRecord)
                .where(CheckpointRecord.session_id == session_id)
                .order_by(CheckpointRecord.iteration.desc())
                .limit(limit)
            )
            rows = result.scalars().all()
            history = []
            for row in rows:
                checkpoint = CheckpointData(
                    session_id=row.session_id,
                    messages=json.loads(row.messages),
                    iteration=row.iteration,
                    status=row.status,
                    tool_results=json.loads(row.tool_results),
                    metadata=json.loads(row.metadata_),
                    channel_values={"thread_id": row.thread_id, "parent_id": row.parent_id or ""},
                )
                history.append((checkpoint, row.id))
            return list(reversed(history))

    async def get_parent_chain(
        self,
        session_id: str,
        checkpoint_id: str,
    ) -> list[tuple[CheckpointData, str]]:
        """获取 checkpoint 的父链 — 从起点到指定 checkpoint 的完整路径"""
        chain: list[tuple[CheckpointData, str]] = []
        current_id: str | None = checkpoint_id

        while current_id:
            cp = await self.get(None, current_id)
            if not cp:
                break
            chain.append((cp, current_id))
            current_id = cp.channel_values.get("parent_id") or None
            if current_id == "":
                current_id = None

        return list(reversed(chain))

    async def fork(
        self,
        session_id: str,
        from_checkpoint_id: str,
        new_messages: list[dict[str, Any]] | None = None,
    ) -> str:
        """从历史 checkpoint 分叉 — 参考 LangGraph update_state

        LangGraph:
            fork_config = graph.update_state(before_joke.config, values={"topic": "chickens"})
            fork_result = graph.invoke(None, fork_config)
        """
        source = await self.get(None, from_checkpoint_id)
        if not source:
            raise ValueError(f"Checkpoint not found: {from_checkpoint_id}")

        # 创建新的 checkpoint，修改消息
        new_checkpoint = CheckpointData(
            session_id=source.session_id,
            messages=new_messages if new_messages is not None else list(source.messages),
            iteration=source.iteration,
            status="forked",
            tool_results=list(source.tool_results),
            metadata={**source.metadata, "forked_from": from_checkpoint_id},
            channel_values={**source.channel_values, "parent_id": from_checkpoint_id},
        )

        return await self.save(
            _thread_id=None,
            checkpoint=new_checkpoint,
            thread_id=source.channel_values.get("thread_id", ""),
            parent_id=from_checkpoint_id,
        )
