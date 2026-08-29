"""Vector memory service — ChromaDB-backed semantic memory retrieval.

- Letta `ArchivalPassage` with ChromaDB embeddings
- Suna lightweight vector memory
- Hermes-Agent reflection memory
"""

from __future__ import annotations

import asyncio
import functools
from datetime import UTC, datetime
from typing import Any

import chromadb
import structlog
from chromadb.api.types import EmbeddingFunction

logger = structlog.get_logger()


class _DefaultEmbeddingWrapper(EmbeddingFunction):
    """Wrap ChromaDB's default embedding function for stability across versions."""

    def __init__(self) -> None:
        pass

    @staticmethod
    def name() -> str:
        return "default"

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> _DefaultEmbeddingWrapper:
        return _DefaultEmbeddingWrapper()

    def get_config(self) -> dict[str, Any]:
        return {}

    def __call__(self, input: list[str]) -> list[list[float]]:
        return self.embed(input)

    def embed(self, input: list[str]) -> list[list[float]]:
        default_ef = chromadb.utils.embedding_functions.DefaultEmbeddingFunction()
        return default_ef(input)


class VectorMemoryService:
    """ChromaDB-backed vector memory for semantic search.

    Collections:
    - episodic: conversation memories and key events
    - archival: long-term archival passages
    - reflection: task reflections and insights
    """

    def __init__(self, persist_directory: str = "./data/chroma") -> None:
        self._client = chromadb.PersistentClient(path=persist_directory)
        self._collections: dict[str, Any] = {}
        self._ef = _DefaultEmbeddingWrapper()

    def _get_collection(self, name: str) -> Any:
        if name not in self._collections:
            self._collections[name] = self._client.get_or_create_collection(
                name=name,
                embedding_function=self._ef,
            )
        return self._collections[name]

    @staticmethod
    def _run(func: Any, *args: Any, **kwargs: Any) -> Any:
        loop = asyncio.get_event_loop()
        if kwargs:
            func = functools.partial(func, **kwargs)
            return loop.run_in_executor(None, func, *args)
        return loop.run_in_executor(None, func, *args)

    async def add(
        self,
        collection: str,
        doc_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Add a document to the vector store."""
        coll = self._get_collection(collection)
        meta = metadata or {}
        meta.setdefault("created_at", datetime.now(UTC).isoformat())
        meta.setdefault("access_count", 0)
        # ChromaDB rejects empty list values in metadata
        meta = {k: v for k, v in meta.items() if not (isinstance(v, list) and len(v) == 0)}
        await self._run(
            coll.add,
            ids=[doc_id],
            documents=[text],
            metadatas=[meta],
        )
        logger.info("vector_memory_added", collection=collection, doc_id=doc_id)
        return doc_id

    async def search(
        self,
        collection: str,
        query: str,
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar documents by semantic similarity."""
        coll = self._get_collection(collection)
        result = await self._run(
            coll.query,
            query_texts=[query],
            n_results=top_k,
            where=where,
        )

        documents: list[dict[str, Any]] = []
        ids = result.get("ids", [[]])[0]
        texts = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        for i, doc_id in enumerate(ids):
            distance = distances[i] if i < len(distances) else 0.0
            documents.append({
                "id": doc_id,
                "text": texts[i] if i < len(texts) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "score": max(0.0, 1.0 - distance),
            })

        logger.info(
            "vector_memory_searched",
            collection=collection,
            query=query,
            results=len(documents),
        )
        return documents

    async def delete(self, collection: str, doc_id: str) -> bool:
        """Delete a document from the vector store."""
        coll = self._get_collection(collection)
        await self._run(coll.delete, ids=[doc_id])
        logger.info("vector_memory_deleted", collection=collection, doc_id=doc_id)
        return True

    async def update_access(self, collection: str, doc_id: str) -> None:
        """Increment access count and update last_accessed timestamp."""
        coll = self._get_collection(collection)
        existing = await self._run(coll.get, ids=[doc_id])

        if existing and existing.get("metadatas"):
            meta = existing["metadatas"][0] or {}
            meta["access_count"] = meta.get("access_count", 0) + 1
            meta["last_accessed"] = datetime.now(UTC).isoformat()
            await self._run(
                coll.update,
                ids=[doc_id],
                metadatas=[meta],
            )
            logger.info(
                "vector_memory_access_updated",
                collection=collection,
                doc_id=doc_id,
            )

    async def get(self, collection: str, doc_id: str) -> dict[str, Any] | None:
        """Get a document by ID."""
        coll = self._get_collection(collection)
        result = await self._run(coll.get, ids=[doc_id])

        if result and result.get("ids") and result["ids"]:
            return {
                "id": result["ids"][0],
                "text": result["documents"][0] if result.get("documents") else "",
                "metadata": result["metadatas"][0] if result.get("metadatas") else {},
            }
        return None

    async def count(self, collection: str) -> int:
        """Count documents in a collection."""
        coll = self._get_collection(collection)
        return await self._run(coll.count)


# Global singleton
vector_memory = VectorMemoryService()
