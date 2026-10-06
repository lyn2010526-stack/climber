"""双层快照管理（innovation_layer，创新点 4）。

基于 langgraph sqlite_checkpoint 思路拓展：
  - 增量 diff 快照：每一轮循环仅存储状态增量（减小 IO）
  - 里程碑全量快照：人机暂停、任务关键节点保存完整会话状态
  - 附加逻辑：连续多轮无进展自动回滚到最近有效里程碑快照重试

学习参考：
  - langgraph/checkpoint/sqlite_checkpoint.py（checkpoint 持久化思路，未复制）
  - agent-system/base_deps/checkpoint_sqlite.py（改写层）
"""

from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any

from agent_system.core_models import Snapshot, TAORPhase


class SnapshotManager:
    """双层快照管理器（SQLite 持久化）。

    表结构：
      snapshots(id, kind, session_id, phase, base_on, payload, created_at, milestone_label)
      snapshot_chain(session_id, head_id)  -- 每会话最新快照指针

    - 增量快照 diff：仅存 messages_delta 与 changed_state_keys
    - 里程碑快照：全量 state + messages
    - 回滚：load_milestone(head) → 还原 state，重试
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._lock = threading.RLock()
        self._conn: sqlite3.Connection | None = None
        self._connect()

    def _connect(self) -> None:
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                session_id TEXT NOT NULL,
                phase TEXT,
                base_on TEXT,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                milestone_label TEXT
            );
            CREATE TABLE IF NOT EXISTS snapshot_chain (
                session_id TEXT PRIMARY KEY,
                head_id TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_snap_session ON snapshots(session_id, created_at);
            """
        )
        self._conn.commit()

    # ---- 保存 ----

    def save_incremental(self, session_id: str, phase: TAORPhase,
                         messages_delta: list[dict[str, Any]],
                         changed_state: dict[str, Any]) -> Snapshot:
        """保存一轮循环的增量 diff 快照。"""
        with self._lock:
            head = self._get_head(session_id)
            snap = Snapshot(
                kind="incremental", session_id=session_id, phase=phase, base_on=head,
                messages_delta=messages_delta,
                diff={"changed_state": changed_state},
            )
            self._conn.execute(
                "INSERT INTO snapshots(id, kind, session_id, phase, base_on, payload, created_at, milestone_label) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (snap.id, snap.kind, session_id, phase.value, snap.base_on,
                 json.dumps({"messages_delta": messages_delta, "changed_state": changed_state}),
                 snap.created_at.isoformat(), None),
            )
            self._set_head(session_id, snap.id)
            self._conn.commit()
        return snap

    def save_milestone(self, session_id: str, phase: TAORPhase,
                       state: dict[str, Any], messages: list[dict[str, Any]],
                       label: str) -> Snapshot:
        """保存里程碑全量快照（人机暂停、关键业务节点）。"""
        with self._lock:
            snap = Snapshot(
                kind="milestone", session_id=session_id, phase=phase,
                state=state, milestone_label=label,
                diff={"messages": messages},
            )
            self._conn.execute(
                "INSERT INTO snapshots(id, kind, session_id, phase, base_on, payload, created_at, milestone_label) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (snap.id, snap.kind, session_id, phase.value, None,
                 json.dumps({"state": state, "messages": messages}),
                 snap.created_at.isoformat(), label),
            )
            self._set_head(session_id, snap.id)
            self._conn.commit()
        return snap

    # ---- 加载 ----

    def load_head(self, session_id: str) -> Snapshot | None:
        """加载最新快照（增量或里程碑，自动沿链合并）。"""
        with self._lock:
            head_id = self._get_head(session_id)
            if head_id is None:
                return None
            return self._load_full(session_id, head_id)

    def load_milestone(self, session_id: str) -> Snapshot | None:
        """加载最近的有效里程碑全量快照（用于无进展回滚）。"""
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM snapshots WHERE session_id=? AND kind='milestone' "
                "ORDER BY created_at DESC LIMIT 1",
                (session_id,),
            ).fetchone()
            if row is None:
                return None
            payload = json.loads(row["payload"])
            return Snapshot(
                id=row["id"], kind=row["kind"], session_id=session_id,
                phase=TAORPhase(row["phase"]) if row["phase"] else None,
                base_on=row["base_on"],
                state=payload.get("state", {}),
                diff={"messages": payload.get("messages", [])},
                created_at=_parse_ts(row["created_at"]),
                milestone_label=row["milestone_label"],
            )

    def list_snapshots(self, session_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, kind, phase, base_on, created_at, milestone_label "
                "FROM snapshots WHERE session_id=? ORDER BY created_at DESC",
                (session_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def count(self, session_id: str | None = None) -> int:
        with self._lock:
            if session_id:
                row = self._conn.execute(
                    "SELECT COUNT(*) AS c FROM snapshots WHERE session_id=?", (session_id,)
                ).fetchone()
            else:
                row = self._conn.execute("SELECT COUNT(*) AS c FROM snapshots").fetchone()
        return row["c"]

    # ---- 回滚 ----

    def rollback_to_milestone(self, session_id: str) -> Snapshot | None:
        """回滚到最近里程碑：返回其 state/messages，供 TAOR 循环重试。"""
        milestone = self.load_milestone(session_id)
        if milestone is None:
            return None
        # 回滚后把链头指回里程碑，丢弃其后增量
        with self._lock:
            self._set_head(session_id, milestone.id)
            self._conn.commit()
        return milestone

    # ---- 内部 ----

    def _get_head(self, session_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT head_id FROM snapshot_chain WHERE session_id=?", (session_id,)
        ).fetchone()
        return row["head_id"] if row else None

    def _set_head(self, session_id: str, snap_id: str) -> None:
        self._conn.execute(
            "INSERT INTO snapshot_chain(session_id, head_id) VALUES (?,?) "
            "ON CONFLICT(session_id) DO UPDATE SET head_id=excluded.head_id",
            (session_id, snap_id),
        )

    def _load_full(self, session_id: str, head_id: str) -> Snapshot:
        """沿链从增量回溯到最近里程碑，重建完整状态。"""
        chain: list[sqlite3.Row] = []
        cursor: str | None = head_id
        while cursor is not None:
            row = self._conn.execute(
                "SELECT * FROM snapshots WHERE id=?", (cursor,)
            ).fetchone()
            if row is None:
                break
            chain.append(row)
            cursor = row["base_on"]
        chain.reverse()  # 从最早的到最新的
        state: dict[str, Any] = {}
        messages: list[dict[str, Any]] = []
        base_snap: Snapshot | None = None
        for row in chain:
            payload = json.loads(row["payload"])
            if row["kind"] == "milestone":
                state = dict(payload.get("state", {}))
                messages = list(payload.get("messages", []))
                base_snap = Snapshot(
                    id=row["id"], kind="milestone", session_id=session_id,
                    phase=TAORPhase(row["phase"]) if row["phase"] else None,
                    state=state, created_at=_parse_ts(row["created_at"]),
                    milestone_label=row["milestone_label"],
                )
            else:
                messages.extend(payload.get("messages_delta", []))
                for k, v in (payload.get("changed_state") or {}).items():
                    state[k] = v
        if base_snap is None and chain:
            # 无里程碑：以链上最早增量为基础
            state = dict(json.loads(chain[0]["payload"]).get("changed_state", {}))
            messages = []
            for row in chain:
                messages.extend(json.loads(row["payload"]).get("messages_delta", []))
        return Snapshot(
            id=head_id, kind="reconstructed", session_id=session_id,
            base_on=base_snap.base_on if base_snap else chain[0]["base_on"] if chain else None,
            state=state, diff={"messages": messages},
            milestone_label=base_snap.milestone_label if base_snap else None,
        )

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None


def _parse_ts(ts: str):
    from datetime import datetime
    return datetime.fromisoformat(ts)
