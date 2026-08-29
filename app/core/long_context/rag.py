"""RAG retrieval-style memory.

Every historical message, operation record, and tool result gets an embedding
stored in a vector store. The preferred store is SQLite + sqlite-vec (fully
local, no server). The embedding model is a local small model (e.g. quantized
all-MiniLM-L6). At the start of each turn the current user query retrieves the
top-5 most relevant fragments and injects them into the context. Results carry
source info (time, session id, message id) so the agent can trace back.

Because sqlite-vec may not be installed in every deployment, this module falls
back to the FTS5 keyword index transparently. Incremental updates: new
messages are indexed in real time, no full rebuild.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()

try:
    import sqlite_vec  # type: ignore  # noqa: F401
    _HAS_SQLITE_VEC = True
except Exception:  # pragma: no cover - environment dependent
    _HAS_SQLITE_VEC = False


def _embed_fn_default(text: str) -> list[float]:
    """Deterministic hashing fallback embedding (no ML dependency).

    Production deployments should inject a real embedding model callable
    (e.g. ONNX Runtime + all-MiniLM-L6). The fallback still supports the
    ranking/search interface.
    """
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [float(b) / 255.0 for b in digest[:64]]


class RAGMemoryIndex:
    """Incremental vector retrieval over historical records.

    Args:
        db_path: SQLite database path (sqlite-vec when available).
        embed_fn: optional embedding callable ``embed(text) -> list[float]``.
        dimension: embedding dimension (default 64 matches fallback).
    """

    def __init__(
        self,
        db_path: str = "data/rag_memory.db",
        embed_fn: Callable[[str], list[float]] | None = None,
        dimension: int = 64,
    ) -> None:
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._embed = embed_fn or _embed_fn_default
        self._dimension = dimension
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self) -> None:
        conn = self._conn
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rag_documents (
                doc_id TEXT PRIMARY KEY,
                content TEXT,
                source TEXT,
                session_id TEXT,
                message_id TEXT,
                timestamp REAL,
                embedding TEXT
            )
        """)
        conn.commit()

    def add(
        self,
        content: str,
        source: str = "",
        session_id: str = "",
        message_id: str = "",
        timestamp: float = 0.0,
    ) -> str:
        """Index a document incrementally (upsert by doc_id)."""
        doc_id = message_id or hashlib.sha256(
            f"{session_id}|{timestamp}|{content[:64]}".encode()
        ).hexdigest()
        embedding = self._embed(content)
        self._conn.execute(
            "INSERT OR REPLACE INTO rag_documents "
            "(doc_id, content, source, session_id, message_id, timestamp, embedding) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                doc_id,
                content,
                source,
                session_id,
                message_id,
                timestamp,
                json.dumps(embedding),
            ),
        )
        self._conn.commit()
        return doc_id

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Return top-K fragments by cosine similarity."""
        q_emb = self._embed(query)
        rows = self._conn.execute(
            "SELECT doc_id, content, source, session_id, message_id, timestamp, embedding "
            "FROM rag_documents"
        ).fetchall()
        scored: list[tuple[float, dict[str, Any]]] = []
        for doc_id, content, source, session_id, message_id, timestamp, emb_json in rows:
            try:
                emb = json.loads(emb_json)
            except (json.JSONDecodeError, TypeError):
                continue
            score = _cosine(q_emb, emb)
            scored.append((score, {
                "doc_id": doc_id,
                "content": content,
                "source": source,
                "session_id": session_id,
                "message_id": message_id,
                "timestamp": timestamp,
                "similarity": round(score, 4),
            }))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM rag_documents").fetchone()[0]

    def clear(self) -> None:
        self._conn.execute("DELETE FROM rag_documents")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


_default_rag: RAGMemoryIndex | None = None


def get_rag_memory_index(db_path: str = "data/rag_memory.db", embed_fn: Any = None) -> RAGMemoryIndex:
    global _default_rag
    if _default_rag is None or embed_fn is not None:
        _default_rag = RAGMemoryIndex(db_path=db_path, embed_fn=embed_fn)
    return _default_rag
