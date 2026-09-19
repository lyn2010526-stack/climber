"""Memory system - three-tier memory management."""

from __future__ import annotations

import contextlib
from collections import deque
from typing import Any

import structlog

logger = structlog.get_logger()


class SessionMemory:
    """Short-term memory: sliding window of recent messages.

    Optionally persists each message to PostgreSQL via a callback.
    """

    def __init__(self, max_messages: int = 50, persist_callback: Any = None):
        self.max_messages = max_messages
        self._messages: deque[dict[str, Any]] = deque(maxlen=max_messages)
        self._persist_callback = persist_callback

    def add(self, role: str, content: str | None, **metadata: Any) -> None:
        message = {
            "role": role,
            "content": content,
            **metadata,
        }
        self._messages.append(message)
        if self._persist_callback is not None:
            with contextlib.suppress(Exception):
                self._persist_callback(message)

    def get_context(self, last_n: int | None = None) -> list[dict[str, Any]]:
        """Get recent messages as context for the model."""
        msgs = list(self._messages)
        if last_n:
            msgs = msgs[-last_n:]
        return msgs

    def clear(self) -> None:
        self._messages.clear()

    def truncate(self, keep_n: int = 10) -> None:
        """Keep only last N messages when context gets too long."""
        while len(self._messages) > keep_n:
            self._messages.popleft()


class LongTermMemory:
    """Long-term memory: persistent facts about user and topics.

    Uses a simple in-memory store. Later can be backed by PostgreSQL.
    """

    def __init__(self):
        # user_id -> list of facts
        self._facts: dict[str, list[dict[str, Any]]] = {}

    def add_fact(self, user_id: str, fact: str, category: str = "general") -> None:
        if user_id not in self._facts:
            self._facts[user_id] = []
        self._facts[user_id].append({
            "fact": fact,
            "category": category,
        })

    def get_facts(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        return self._facts.get(user_id, [])[-limit:]

    def format_for_prompt(self, user_id: str) -> str:
        facts = self.get_facts(user_id)
        if not facts:
            return ""
        lines = ["## Known Facts:"]
        for f in facts:
            lines.append(f"- [{f['category']}] {f['fact']}")
        return "\n".join(lines)


class VectorMemory:
    """RAG memory: document chunks stored as vectors.

    Uses Chroma as the embedded vector database.
    """

    def __init__(self, persist_path: str = "./data/chroma"):
        self.persist_path = persist_path
        self._client = None
        self._collections: dict[str, Any] = {}

    async def _get_client(self):
        if self._client is None:
            import chromadb
            self._client = chromadb.PersistentClient(path=self.persist_path)
        return self._client

    async def _get_collection(self, name: str):
        if name not in self._collections:
            client = await self._get_client()
            self._collections[name] = client.get_or_create_collection(name)
        return self._collections[name]

    async def add_documents(
        self,
        collection: str,
        documents: list[str],
        ids: list[str] | None = None,
        metadatas: list[dict] | None = None,
    ) -> None:
        """Add text chunks to a collection. Uses default embedding (all-MiniLM)."""
        coll = await self._get_collection(collection)
        if ids is None:
            import uuid
            ids = [str(uuid.uuid4()) for _ in documents]
        coll.add(documents=documents, ids=ids, metadatas=metadatas)

    async def query(
        self,
        collection: str,
        query_text: str,
        n_results: int = 5,
    ) -> list[str]:
        """Search for relevant chunks."""
        coll = await self._get_collection(collection)
        try:
            results = coll.query(query_texts=[query_text], n_results=n_results)
            docs = results.get("documents", [[]])
            return docs[0] if docs else []
        except Exception as e:
            logger.warning("Vector query failed", error=str(e))
            return []
