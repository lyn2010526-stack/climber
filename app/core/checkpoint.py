"""Checkpoint storage for agent sessions.

- LangGraph `checkpoint/` 检查点快照机制
- OpenCode `session/` Session 状态模型
"""

from __future__ import annotations

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
