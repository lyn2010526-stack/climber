"""Document processing and knowledge base management.

Provides in-memory storage for documents and their chunks, along with
keyword-based retrieval across titles and contents.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class DocType(StrEnum):
    """Document type classification."""

    MARKDOWN = "markdown"
    CODE = "code"
    TEXT = "text"
    CONFIG = "config"
    JSON = "json"


class KnowledgeDoc(BaseModel):
    """A stored knowledge document."""

    id: str
    title: str
    content: str
    doc_type: DocType = DocType.TEXT
    tags: list[str] = Field(default_factory=list)
    source: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    chunk_count: int = 0


class KnowledgeChunk(BaseModel):
    """A single chunk extracted from a knowledge document."""

    id: str
    doc_id: str
    content: str
    chunk_index: int
    token_count: int


class KnowledgeBase:
    """In-memory knowledge base with chunking and keyword search."""

    def __init__(self) -> None:
        self._docs: dict[str, KnowledgeDoc] = {}
        self._chunks: dict[str, list[KnowledgeChunk]] = {}

    async def add_document(
        self,
        title: str,
        content: str,
        doc_type: DocType = DocType.TEXT,
        tags: list[str] | None = None,
        source: str | None = None,
    ) -> KnowledgeDoc:
        """Add a document, chunking its content into manageable pieces."""
        doc_id = uuid.uuid4().hex
        chunks = self._chunk_text(content)
        chunk_models: list[KnowledgeChunk] = []
        for index, chunk in enumerate(chunks):
            chunk_models.append(
                KnowledgeChunk(
                    id=f"{doc_id}:{index}",
                    doc_id=doc_id,
                    content=chunk,
                    chunk_index=index,
                    token_count=self._token_count(chunk),
                )
            )
        doc = KnowledgeDoc(
            id=doc_id,
            title=title,
            content=content,
            doc_type=doc_type,
            tags=tags or [],
            source=source,
            chunk_count=len(chunk_models),
        )
        self._docs[doc_id] = doc
        self._chunks[doc_id] = chunk_models
        logger.info("knowledge_base.document_added", doc_id=doc_id, chunks=len(chunk_models))
        return doc

    async def get_document(self, doc_id: str) -> KnowledgeDoc | None:
        """Retrieve a document by id, or None if not found."""
        return self._docs.get(doc_id)

    async def delete_document(self, doc_id: str) -> bool:
        """Delete a document and its chunks, returning True if it existed."""
        if doc_id not in self._docs:
            return False
        del self._docs[doc_id]
        self._chunks.pop(doc_id, None)
        logger.info("knowledge_base.document_deleted", doc_id=doc_id)
        return True

    async def list_documents(self, limit: int = 50) -> list[KnowledgeDoc]:
        """List documents, most recently added first, capped at limit."""
        docs = sorted(self._docs.values(), key=lambda d: d.created_at, reverse=True)
        return docs[:limit]

    async def search(
        self,
        query: str,
        doc_type: DocType | None = None,
        top_k: int = 5,
    ) -> list[KnowledgeDoc]:
        """Keyword search over titles and contents, matching case-insensitively."""
        needle = query.strip().lower()
        if not needle:
            return []
        candidates = list(self._docs.values())
        if doc_type is not None:
            candidates = [d for d in candidates if d.doc_type == doc_type]
        scored: list[tuple[int, KnowledgeDoc]] = []
        for doc in candidates:
            title_score = 1 if needle in doc.title.lower() else 0
            content_score = 1 if needle in doc.content.lower() else 0
            score = title_score + content_score
            if score:
                scored.append((score, doc))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]

    async def get_chunks(self, doc_id: str) -> list[KnowledgeChunk]:
        """Return all chunks for a document in index order."""
        return self._chunks.get(doc_id, [])

    def _chunk_text(self, content: str, max_chars: int = 800) -> list[str]:
        """Split content into chunks by paragraphs and sentences, each at most max_chars."""
        if not content:
            return []
        paragraphs = [p.strip() for p in content.split("\n") if p.strip()]
        if not paragraphs:
            paragraphs = [content.strip()]
        chunks: list[str] = []
        for paragraph in paragraphs:
            if len(paragraph) <= max_chars:
                chunks.append(paragraph)
                continue
            buffer = ""
            for sentence in self._split_sentences(paragraph):
                for piece in self._split_long(sentence, max_chars):
                    if len(buffer) + len(piece) + 1 > max_chars and buffer:
                        chunks.append(buffer)
                        buffer = piece
                    else:
                        buffer = f"{buffer} {piece}".strip() if buffer else piece
            if buffer:
                chunks.append(buffer)
        return [c.strip() for c in chunks if c.strip()]

    @staticmethod
    def _split_long(text: str, max_chars: int) -> list[str]:
        """Split an overlong sentence into fixed-size pieces."""
        pieces: list[str] = []
        for start in range(0, len(text), max_chars):
            pieces.append(text[start : start + max_chars])
        return pieces

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Split text into sentences on terminal punctuation, preserving the markers."""
        parts: list[str] = []
        current = ""
        for char in text:
            current += char
            if char in ".。!！?？;；":
                parts.append(current)
                current = ""
        if current:
            parts.append(current)
        return [p for p in parts if p.strip()]

    def _token_count(self, text: str) -> int:
        """Estimate token count as one token per four characters."""
        return len(text) // 4


_knowledge_base: KnowledgeBase | None = None


async def get_knowledge_base() -> KnowledgeBase:
    """Return the shared knowledge base singleton."""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
    return _knowledge_base
