"""FTS5 关键词记忆检索层（base_deps）。

改写自 Hermes-Agent `plugins/memory/holographic/holographic_store.py` 与
`retrieval.py` 的设计思路：SQLite FTS5 建表、事实存储、检索打分、时间衰减、
trust_score 可信度权重计算。非原样复制，仅保留 FTS5 架构概念，实现为原创。

学习要点（见 Hermes-Agent）：
  - FTS5 虚拟表 + external content 与主表关联
  - trust_score（可信度）与时间衰减（decay）联合加权
  - 关键词匹配得分（bm25）叠加业务权重

遵循约束：不复制 Hermes 源码，仅改写其设计；本文件保留概念性参考标注。
"""

from __future__ import annotations

import json
import math
import sqlite3
import threading
from datetime import datetime
from typing import Any

from agent_system.core_models import MemoryItem, MemoryKind, RetrievedMemory, now_utc

DEFAULT_HALF_LIFE_SECONDS = 7 * 24 * 3600  # 默认时间衰减半衰期（7 天）


class Fts5Store:
    """SQLite FTS5 事实/关键词记忆存储。

    - 主表 memory_items：权威记忆行（含 trust_score、decay、metadata JSON）
    - FTS5 虚拟表 memory_fts：全文索引（title + text），external content 关联主表
    - 检索：bm25 关键词得分 * 时间衰减 * trust_score 加权，返回 RetrievedMemory
    """

    def __init__(self, db_path: str, half_life_seconds: float = DEFAULT_HALF_LIFE_SECONDS) -> None:
        self.db_path = db_path
        self.half_life = half_life_seconds
        self._lock = threading.RLock()
        self._conn: sqlite3.Connection | None = None
        self._connect()

    def _connect(self) -> None:
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS memory_items (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    text TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    doc_type TEXT,
                    doc_length INTEGER NOT NULL DEFAULT 0,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    trust_score REAL NOT NULL DEFAULT 0.5,
                    decay REAL NOT NULL DEFAULT 1.0,
                    created_at TEXT NOT NULL,
                    last_accessed_at TEXT,
                    accessed_count INTEGER NOT NULL DEFAULT 0,
                    ttl_seconds INTEGER,
                    source_session TEXT,
                    structured TEXT NOT NULL DEFAULT '{}'
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                    title, text, content='memory_items', content_rowid='rowid',
                    tokenize='trigram'
                );

                CREATE INDEX IF NOT EXISTS idx_memory_kind ON memory_items(kind);
                CREATE INDEX IF NOT EXISTS idx_memory_doc_type ON memory_items(doc_type);
                """
            )
            self._conn.commit()

    # ---- 写入 ----

    def upsert(self, item: MemoryItem) -> str:
        """插入或更新一条记忆并同步 FTS 索引。"""
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO memory_items (
                    id, kind, text, title, doc_type, doc_length, metadata,
                    trust_score, decay, created_at, last_accessed_at, accessed_count,
                    ttl_seconds, source_session, structured
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    kind=excluded.kind, text=excluded.text, title=excluded.title,
                    doc_type=excluded.doc_type, doc_length=excluded.doc_length,
                    metadata=excluded.metadata, trust_score=excluded.trust_score,
                    decay=excluded.decay, ttl_seconds=excluded.ttl_seconds,
                    source_session=excluded.source_session, structured=excluded.structured
                """,
                (
                    item.id, item.kind.value, item.text, item.title, item.doc_type,
                    item.doc_length, json.dumps(item.metadata, ensure_ascii=False),
                    item.trust_score, item.decay,
                    item.created_at.isoformat(),
                    item.last_accessed_at.isoformat() if item.last_accessed_at else None,
                    item.accessed_count, item.ttl_seconds, item.source_session,
                    json.dumps(item.structured, ensure_ascii=False),
                ),
            )
            rowid = self._conn.execute(
                "SELECT rowid FROM memory_items WHERE id=?", (item.id,)
            ).fetchone()["rowid"]
            self._conn.execute(
                "INSERT OR REPLACE INTO memory_fts(rowid, title, text) VALUES (?, ?, ?)",
                (rowid, item.title, item.text),
            )
            self._conn.commit()
        return item.id

    # ---- 检索 ----

    def search(self, query: str, top_k: int = 10, kinds: list[str] | None = None,
               min_trust: float = 0.0, include_expired: bool = False) -> list[RetrievedMemory]:
        """FTS5 关键词检索 + 可信度 + 时间衰减加权。

        返回按融合分倒序的 RetrievedMemory 列表。
        """
        now = now_utc()
        where = ["memory_fts MATCH ?"]
        params: list[Any] = [f'"{query}"' if _needs_quote(query) else query]
        if kinds:
            placeholders = ",".join("?" * len(kinds))
            where.append(f"m.kind IN ({placeholders})")
            params.extend(kinds)
        if not include_expired:
            # TTL 过期清理：未过期 = (ttl_seconds 为空 或 last_accessed 为空 或 last_accessed+ttl > now)
            where.append(
                "(m.ttl_seconds IS NULL OR "
                "m.last_accessed_at IS NULL OR "
                "datetime(m.last_accessed_at, '+' || m.ttl_seconds || ' seconds') > datetime(?))"
            )
            params.append(now.isoformat())
        where_sql = " WHERE " + " AND ".join(where)
        with self._lock:
            # 结构部分由代码拼接，所有取值均走 `?` 参数绑定，无注入面。
            query = (
                "SELECT m.id, m.kind, m.text, m.title, m.doc_type, m.doc_length, "  # noqa: S608
                "m.metadata, m.trust_score, m.decay, m.created_at, "
                "m.last_accessed_at, m.accessed_count, m.ttl_seconds, "
                "m.source_session, m.structured, "
                "bm25(memory_fts) AS raw_score "
                "FROM memory_fts JOIN memory_items m ON m.rowid = memory_fts.rowid "
                f"{where_sql} "
                "ORDER BY raw_score "
                "LIMIT ?"
            )
            rows = self._conn.execute(query, [*params, top_k * 3]).fetchall()

        results: list[RetrievedMemory] = []
        for row in rows:
            item = _row_to_item(row)
            if item.trust_score < min_trust:
                continue
            keyword_score = _normalize_bm25(row["raw_score"])
            decay = _time_decay(item, now, self.half_life)
            score = keyword_score * decay * (0.5 + item.trust_score)
            results.append(RetrievedMemory(
                item=item, route="fts", score=round(score, 4),
                keyword_score=round(keyword_score, 4),
                reason=f"bm25={row['raw_score']:.2f} decay={decay:.2f} trust={item.trust_score:.2f}",
            ))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def get(self, memory_id: str) -> MemoryItem | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM memory_items WHERE id=?", (memory_id,)
            ).fetchone()
        return _row_to_item(row) if row else None

    def list_all(self, limit: int = 1000) -> list[MemoryItem]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM memory_items ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_row_to_item(r) for r in rows]

    def touch(self, memory_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE memory_items SET last_accessed_at=?, accessed_count=accessed_count+1 "
                "WHERE id=?",
                (now_utc().isoformat(), memory_id),
            )
            self._conn.commit()

    def update_trust(self, memory_id: str, new_trust: float, decay: float | None = None) -> None:
        with self._lock:
            if decay is not None:
                self._conn.execute(
                    "UPDATE memory_items SET trust_score=?, decay=? WHERE id=?",
                    (new_trust, decay, memory_id),
                )
            else:
                self._conn.execute(
                    "UPDATE memory_items SET trust_score=? WHERE id=?",
                    (new_trust, memory_id),
                )
            self._conn.commit()

    def delete(self, memory_id: str) -> None:
        with self._lock:
            row = self._conn.execute(
                "SELECT rowid FROM memory_items WHERE id=?", (memory_id,)
            ).fetchone()
            if row:
                self._conn.execute("DELETE FROM memory_fts WHERE rowid=?", (row["rowid"],))
            self._conn.execute("DELETE FROM memory_items WHERE id=?", (memory_id,))
            self._conn.commit()

    def count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) AS c FROM memory_items").fetchone()["c"]

    def expire_ttl(self) -> int:
        """清理 TTL 过期记忆，返回清理条数（Mnemosyne 思路）。"""
        with self._lock:
            now = now_utc().isoformat()
            rows = self._conn.execute(
                "SELECT id FROM memory_items WHERE ttl_seconds IS NOT NULL "
                "AND last_accessed_at IS NOT NULL AND "
                "datetime(last_accessed_at, '+' || ttl_seconds || ' seconds') <= datetime(?)",
                (now,),
            ).fetchall()
            for row in rows:
                self.delete(row["id"])
            return len(rows)

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None


def _needs_quote(query: str) -> bool:
    return any(ch in query for ch in " ()*:\"'\\")


def _normalize_bm25(raw: float) -> float:
    """bm25 负分归一化到 (0, 1]。"""
    if raw is None:
        return 0.0
    return 1.0 / (1.0 + math.exp(-raw / 5.0))


def _time_decay(item: MemoryItem, now: datetime, half_life: float) -> float:
    """指数时间衰减：越久未访问权重越低（Hermes 思路，原创公式）。"""
    last = item.last_accessed_at or item.created_at
    age_seconds = (now - last).total_seconds()
    return math.exp(-age_seconds / half_life) if age_seconds > 0 else 1.0


def _row_to_item(row: sqlite3.Row) -> MemoryItem:
    return MemoryItem(
        id=row["id"],
        kind=MemoryKind(row["kind"]),
        text=row["text"],
        title=row["title"] or "",
        doc_type=row["doc_type"],
        doc_length=row["doc_length"] or 0,
        metadata=json.loads(row["metadata"] or "{}"),
        trust_score=row["trust_score"] or 0.5,
        decay=row["decay"] or 1.0,
        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else now_utc(),
        last_accessed_at=datetime.fromisoformat(row["last_accessed_at"])
        if row["last_accessed_at"] else None,
        accessed_count=row["accessed_count"] or 0,
        ttl_seconds=row["ttl_seconds"],
        source_session=row["source_session"],
        structured=json.loads(row["structured"] or "{}"),
    )
