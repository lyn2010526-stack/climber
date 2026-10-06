"""Vector memory service — ChromaDB-backed semantic memory retrieval.

- Letta `ArchivalPassage` with ChromaDB embeddings
- Suna lightweight vector memory
- Hermes-Agent reflection memory
"""

from __future__ import annotations

import asyncio
import functools
import hashlib
import math
import re
from datetime import UTC, datetime
from typing import Any, cast

import structlog

logger = structlog.get_logger()

# ChromaDB is optional: keep imports local so the module (and everything that
# imports it) degrades gracefully when the package is not installed.
try:
    import chromadb
    from chromadb.api.types import EmbeddingFunction
except Exception:  # pragma: no cover - Chroma is optional
    chromadb = None  # type: ignore[assignment]  # optional dependency absent
    EmbeddingFunction = Any  # type: ignore[misc, assignment]  # dynamic fallback base

_COLLECTION_NAME_RE = re.compile(r"[^a-zA-Z0-9._-]")

# Chroma's default embedding function (all-MiniLM-L6-v2) uses 384 dimensions;
# the offline fallback matches it so both can share a single collection.
_EMBED_DIM = 384


class _DefaultEmbeddingWrapper(EmbeddingFunction):  # type: ignore[type-arg]  # chromadb protocol is generic
    """Wrap ChromaDB's default embedding function for stability across versions."""

    def __init__(self) -> None:
        self._default_ef: Any = None

    @staticmethod
    def name() -> str:
        return "default"

    def __call__(self, input: list[str]) -> list[list[float]]:  # type: ignore[override]  # protocol returns ndarrays
        return self.embed(input)

    def embed(self, input: list[str]) -> list[list[float]]:
        """Embed text, degrading to a deterministic offline fallback on failure."""
        if chromadb is not None:
            if self._default_ef is None:
                try:
                    self._default_ef = cast(
                        "Any", chromadb
                    ).utils.embedding_functions.DefaultEmbeddingFunction()
                except Exception:
                    self._default_ef = None
            if self._default_ef is not None:
                try:
                    return cast("list[list[float]]", self._default_ef(input))
                except Exception:
                    logger.debug("default embedding failed, using offline fallback")
        return self._fallback_embed(input)

    @staticmethod
    def _fallback_embed(texts: list[str]) -> list[list[float]]:
        """Deterministic offline embedding: token hash bags normalised to unit length."""
        vectors: list[list[float]] = []
        for text in texts:
            vec = [0.0] * _EMBED_DIM
            tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower()) or [text]
            for tok in tokens:
                digest = hashlib.sha256(tok.encode()).hexdigest()
                idx = int(digest[:8], 16) % _EMBED_DIM
                sign = (
                    1.0
                    if int(hashlib.sha256(f"{tok}:s".encode()).hexdigest()[:8], 16) % 2
                    else -1.0
                )
                vec[idx] += sign
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vectors.append([v / norm for v in vec])
        return vectors


class VectorMemoryService:
    """ChromaDB-backed vector memory for semantic search.

    Collections:
    - episodic: conversation memories and key events
    - archival: long-term archival passages
    - reflection: task reflections and insights
    """

    def __init__(self, persist_directory: str | None = None) -> None:
        if persist_directory is None:
            from app.config import settings

            persist_directory = getattr(settings, "vector_store_path", "./data/chroma")
        # The client is created lazily on first use so importing this module
        # (and constructing the singleton below) has no Chroma side effects.
        self._persist_directory = persist_directory
        self._client: Any = None
        self._collections: dict[str, Any] = {}
        self._ef = _DefaultEmbeddingWrapper()

    def _ensure_client(self) -> Any:
        """Create the Chroma client lazily; raises when Chroma is unavailable."""
        if chromadb is None:
            raise RuntimeError("chromadb is not installed")
        if self._client is None:
            self._client = chromadb.PersistentClient(path=self._persist_directory)
        return self._client

    async def _get_collection(self, name: str) -> Any:
        safe_name = _COLLECTION_NAME_RE.sub("_", name)
        if safe_name not in self._collections:
            client = await self._run(self._ensure_client)
            self._collections[safe_name] = await self._run(
                client.get_or_create_collection,
                name=safe_name,
                embedding_function=self._ef,
            )
        return self._collections[safe_name]

    @staticmethod
    def _run(func: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError as exc:
            raise RuntimeError(
                "VectorMemoryService._run must be called from an async context"
            ) from exc
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
        coll = await self._get_collection(collection)
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
        profile_context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar documents by semantic similarity."""
        coll = await self._get_collection(collection)
        result = await self._run(
            coll.query,
            query_texts=[query],
            n_results=max(top_k, top_k * 2 if profile_context else top_k),
            where=where,
        )

        documents: list[dict[str, Any]] = []
        ids = result.get("ids", [[]])[0]
        texts = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        for i, doc_id in enumerate(ids):
            distance = distances[i] if i < len(distances) else 0.0
            documents.append(
                {
                    "id": doc_id,
                    "text": texts[i] if i < len(texts) else "",
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "score": max(0.0, 1.0 - distance),
                }
            )

        if profile_context:
            documents = rank_with_profile(documents, profile_context)[:top_k]

        logger.info(
            "vector_memory_searched",
            collection=collection,
            query=query,
            results=len(documents),
        )
        return documents

    async def delete(self, collection: str, doc_id: str) -> bool:
        """Delete a document from the vector store."""
        coll = await self._get_collection(collection)
        await self._run(coll.delete, ids=[doc_id])
        logger.info("vector_memory_deleted", collection=collection, doc_id=doc_id)
        return True

    async def update_access(self, collection: str, doc_id: str) -> None:
        """Increment access count and update last_accessed timestamp."""
        coll = await self._get_collection(collection)
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
        coll = await self._get_collection(collection)
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
        coll = await self._get_collection(collection)
        return cast("int", await self._run(coll.count))


# Global singleton
vector_memory = VectorMemoryService()


def rank_with_profile(
    documents: list[dict[str, Any]], profile_context: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """Apply a bounded preference boost to already privacy-scoped results."""
    if not documents or not profile_context or profile_context.get("enabled") is False:
        return documents
    confidence = profile_context.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)) or confidence <= 0:
        return documents
    confidence = min(1.0, float(confidence))
    preferences = {
        key: profile_context.get(key, {})
        for key in ("task_preferences", "tool_preferences", "reasoning_preferences")
    }
    for document in documents:
        metadata = document.get("metadata") or {}
        boost = 0.0
        for field, preference_key in (
            ("task_type", "task_preferences"),
            ("tool", "tool_preferences"),
            ("reasoning_level", "reasoning_preferences"),
        ):
            value = metadata.get(field)
            values = preferences[preference_key]
            if isinstance(value, str) and isinstance(values, dict):
                score = values.get(value, 0.0)
                if isinstance(score, (int, float)):
                    boost += min(1.0, max(0.0, float(score)))
        document["profile_score"] = round(boost * confidence, 4)
        document["score"] = round(
            float(document.get("score", 0.0)) + 0.2 * document["profile_score"], 4
        )
    return sorted(documents, key=lambda item: item.get("score", 0.0), reverse=True)
