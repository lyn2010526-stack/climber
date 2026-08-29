"""SQLite FTS5 full-text index for cross-session history search.

All historical conversation messages, tool results, and decisions are indexed
in a SQLite FTS5 table. The ``search_memory`` function retrieves the top-5
most relevant fragments by BM25 scoring, injecting them into the context.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

_local = threading.local()


def _get_conn(db_path: str) -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        _create_fts_table(conn)
        _local.conn = conn
    return _local.conn


def _create_fts_table(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
            content,
            source,
            session_id,
            message_id,
            timestamp,
            tokenize='unicode61'
        );
    """)
    conn.commit()


class FTS5MemoryIndex:
    """Full-text index over session history, using SQLite FTS5.

    Args:
        db_path: path to the SQLite database file.
    """

    def __init__(self, db_path: str = "data/memory_fts.db") -> None:
        self._db_path = db_path
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

    def _conn(self) -> sqlite3.Connection:
        return _get_conn(self._db_path)

    def index(
        self,
        content: str,
        source: str = "",
        session_id: str = "",
        message_id: str = "",
        timestamp: float = 0.0,
    ) -> None:
        conn = self._conn()
        conn.execute(
            "INSERT INTO memory_fts(content, source, session_id, message_id, timestamp) VALUES (?, ?, ?, ?, ?)",
            (content, source, session_id, message_id, str(timestamp)),
        )
        conn.commit()

    def index_dict(self, record: dict[str, Any]) -> None:
        self.index(
            content=json.dumps(record, ensure_ascii=False, default=str),
            source=record.get("source", ""),
            session_id=record.get("session_id", ""),
            message_id=record.get("message_id", ""),
            timestamp=record.get("timestamp", 0.0),
        )

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT content, source, session_id, message_id, timestamp, rank "
                "FROM memory_fts WHERE content MATCH ? "
                "ORDER BY rank LIMIT ?",
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            # FTS5 syntax error in query — fall back to LIKE
            rows = conn.execute(
                "SELECT content, source, session_id, message_id, timestamp, 0.0 "
                "FROM memory_fts WHERE content LIKE ? "
                "LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
        return [
            {
                "content": row[0],
                "source": row[1],
                "session_id": row[2],
                "message_id": row[3],
                "timestamp": row[4],
                "rank": row[5],
            }
            for row in rows
        ]

    def count(self) -> int:
        conn = self._conn()
        return conn.execute("SELECT COUNT(*) FROM memory_fts").fetchone()[0]

    def clear(self) -> None:
        conn = self._conn()
        conn.execute("DELETE FROM memory_fts")
        conn.commit()

    def close(self) -> None:
        conn = getattr(_local, "conn", None)
        if conn is not None:
            conn.close()
            _local.conn = None


_default_fts: FTS5MemoryIndex | None = None


def get_fts5_index(db_path: str = "data/memory_fts.db") -> FTS5MemoryIndex:
    global _default_fts
    if _default_fts is None:
        _default_fts = FTS5MemoryIndex(db_path=db_path)
    return _default_fts


async def search_memory(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Public tool: search indexed history with FTS5 full-text search."""
    index = get_fts5_index()
    return index.search(query, limit=limit)
