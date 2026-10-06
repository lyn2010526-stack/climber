"""SQLite 检查点持久化（base_deps）。

改写自 langgraph `checkpoint/sqlite.py` 的设计思路：以
`(thread_id, checkpoint_id)` 为键把运行时状态落到 SQLite，
支持保存/加载/清理。非原样复制，仅保留"外部存储状态快照"的概念，
实现为原创的轻量 JSON 存储。

与 agent-system/innovation_layer/dual_snapshot.py 的分工：
  - 本文件：通用 checkpoint（任意 session 状态，按需存任意轮次）
  - dual_snapshot：双层快照（增量 diff + 里程碑全量 + 链重建 + 回滚）
两者可共存：checkpoint 用于粗粒度恢复点，快照用于细粒度审计/回滚。
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime
from typing import Any


class SqliteCheckpointStore:
    """线程安全的 SQLite 检查点存储。

    表结构：
      checkpoints(
        thread_id TEXT, checkpoint_id TEXT,
        state TEXT NOT NULL, created_at TEXT NOT NULL,
        PRIMARY KEY (thread_id, checkpoint_id)
      )
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS checkpoints (
                thread_id TEXT NOT NULL,
                checkpoint_id TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (thread_id, checkpoint_id)
            )
            """
        )
        self._conn.commit()

    def save(self, thread_id: str, checkpoint_id: str, state: dict[str, Any]) -> None:
        """保存一个检查点（覆盖同键）。"""
        payload = json.dumps(state, ensure_ascii=False, default=str)
        with self._lock:
            self._conn.execute(
                "INSERT INTO checkpoints(thread_id, checkpoint_id, state, created_at) "
                "VALUES (?,?,?,?) "
                "ON CONFLICT(thread_id, checkpoint_id) DO UPDATE SET "
                "state=excluded.state, created_at=excluded.created_at",
                (thread_id, checkpoint_id, payload, _now_iso()),
            )
            self._conn.commit()

    def load(self, thread_id: str, checkpoint_id: str | None = None) -> dict[str, Any] | None:
        """加载指定检查点；checkpoint_id 为空时加载该线程最新一个。"""
        with self._lock:
            if checkpoint_id:
                row = self._conn.execute(
                    "SELECT state FROM checkpoints WHERE thread_id=? AND checkpoint_id=?",
                    (thread_id, checkpoint_id),
                ).fetchone()
            else:
                row = self._conn.execute(
                    "SELECT state FROM checkpoints WHERE thread_id=? "
                    "ORDER BY created_at DESC LIMIT 1",
                    (thread_id,),
                ).fetchone()
        return json.loads(row["state"]) if row else None

    def list_ids(self, thread_id: str) -> list[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT checkpoint_id FROM checkpoints WHERE thread_id=? ORDER BY created_at",
                (thread_id,),
            ).fetchall()
        return [r["checkpoint_id"] for r in rows]

    def latest(self, thread_id: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT checkpoint_id FROM checkpoints WHERE thread_id=? "
                "ORDER BY created_at DESC LIMIT 1",
                (thread_id,),
            ).fetchone()
        return row["checkpoint_id"] if row else None

    def purge(self, thread_id: str | None = None) -> int:
        with self._lock:
            if thread_id:
                cur = self._conn.execute(
                    "DELETE FROM checkpoints WHERE thread_id=?", (thread_id,)
                )
            else:
                cur = self._conn.execute("DELETE FROM checkpoints")
            self._conn.commit()
            return cur.rowcount

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
