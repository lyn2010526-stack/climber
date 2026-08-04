"""Knowledge system for multi-agent crews.

Provides document-based knowledge sources that agents can reference:
- PDFKnowledgeSource: PDF document parsing
- CSVKnowledgeSource: CSV data loading
- JSONKnowledgeSource: JSON data loading
- TextKnowledgeSource: Plain text content
- KnowledgeManager: unified interface for querying all sources
"""

from __future__ import annotations

import csv
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class Document(BaseModel):
    """A single document chunk from a knowledge source."""

    content: str
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float = 0.0


class KnowledgeSource(ABC):
    """Abstract knowledge source that agents can query."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._documents: list[Document] = []
        self._loaded = False

    @abstractmethod
    async def load(self) -> list[Document]:
        """Load documents from the source."""
        ...

    async def query(self, query: str, limit: int = 5) -> list[Document]:
        """Query documents by relevance to the query string.

        Performs simple keyword matching by default. Subclasses can
        override for vector-based or more sophisticated retrieval.
        """
        if not self._loaded:
            await self.ensure_loaded()

        if not query.strip():
            return self._documents[:limit]

        query_lower = query.lower()
        query_terms = set(query_lower.split())

        scored: list[tuple[float, Document]] = []
        for doc in self._documents:
            doc_lower = doc.content.lower()
            matches = sum(1 for term in query_terms if term in doc_lower)
            if matches > 0:
                score = matches / len(query_terms)
                scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, doc in scored[:limit]:
            doc.score = score
            results.append(doc)
        return results

    async def ensure_loaded(self) -> None:
        """Ensure documents are loaded."""
        if not self._loaded:
            self._documents = await self.load()
            self._loaded = True

    def reset(self) -> None:
        """Reset the loaded state to force reload."""
        self._documents = []
        self._loaded = False


class PDFKnowledgeSource(KnowledgeSource):
    """PDF document knowledge source.

    Loads text from PDF files and chunks them into documents.
    """

    def __init__(
        self,
        name: str,
        file_path: str,
        description: str = "",
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
    ):
        super().__init__(name, description)
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    async def load(self) -> list[Document]:
        """Load and chunk PDF content."""
        path = Path(self.file_path)
        if not path.exists():
            logger.error("pdf_source_not_found", path=self.file_path)
            return []

        try:
            text = await self._extract_text(path)
            chunks = self._chunk_text(text)
            documents = [
                Document(
                    content=chunk,
                    source=f"{self.name}:{i}",
                    metadata={"file": self.file_path, "chunk_index": i},
                )
                for i, chunk in enumerate(chunks)
            ]
            logger.info("pdf_source_loaded", name=self.name, chunks=len(documents))
            return documents
        except Exception as e:
            logger.error("pdf_source_load_failed", name=self.name, error=str(e))
            return []

    async def _extract_text(self, path: Path) -> str:
        """Extract text from a PDF file."""
        try:
            import pypdf

            reader = pypdf.PdfReader(str(path))
            text_parts: list[str] = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n\n".join(text_parts)
        except ImportError:
            logger.warning("pypdf_not_available", fallback="basic_extraction")
            return f"[PDF content from {path.name}]"

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks."""
        if len(text) <= self.chunk_size:
            return [text]

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end])
            start += self.chunk_size - self.chunk_overlap
        return chunks


class CSVKnowledgeSource(KnowledgeSource):
    """CSV data knowledge source.

    Loads CSV files and converts rows to document chunks.
    """

    def __init__(
        self,
        name: str,
        file_path: str,
        description: str = "",
        text_columns: list[str] | None = None,
        max_rows_per_doc: int = 50,
    ):
        super().__init__(name, description)
        self.file_path = file_path
        self.text_columns = text_columns
        self.max_rows_per_doc = max_rows_per_doc

    async def load(self) -> list[Document]:
        """Load CSV data into documents."""
        path = Path(self.file_path)
        if not path.exists():
            logger.error("csv_source_not_found", path=self.file_path)
            return []

        try:
            documents: list[Document] = []
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            for i in range(0, len(rows), self.max_rows_per_doc):
                batch = rows[i : i + self.max_rows_per_doc]
                content_parts: list[str] = []

                for row in batch:
                    if self.text_columns:
                        parts = [f"{col}: {row.get(col, '')}" for col in self.text_columns if col in row]
                        content_parts.append(" | ".join(parts))
                    else:
                        content_parts.append(" | ".join(f"{k}: {v}" for k, v in row.items()))

                documents.append(Document(
                    content="\n".join(content_parts),
                    source=f"{self.name}:batch{i // self.max_rows_per_doc}",
                    metadata={"file": self.file_path, "batch": i // self.max_rows_per_doc},
                ))

            logger.info("csv_source_loaded", name=self.name, docs=len(documents))
            return documents
        except Exception as e:
            logger.error("csv_source_load_failed", name=self.name, error=str(e))
            return []


class JSONKnowledgeSource(KnowledgeSource):
    """JSON data knowledge source.

    Loads JSON files and converts items to documents.
    """

    def __init__(
        self,
        name: str,
        file_path: str,
        description: str = "",
        content_path: str | None = None,
    ):
        super().__init__(name, description)
        self.file_path = file_path
        self.content_path = content_path

    async def load(self) -> list[Document]:
        """Load JSON data into documents."""
        path = Path(self.file_path)
        if not path.exists():
            logger.error("json_source_not_found", path=self.file_path)
            return []

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            documents: list[Document] = []

            if self.content_path:
                for key in self.content_path.split("."):
                    if isinstance(data, dict):
                        data = data.get(key, [])
                    elif isinstance(data, list) and key.isdigit():
                        data = data[int(key)]

            items = data if isinstance(data, list) else [data]

            for i, item in enumerate(items):
                if isinstance(item, dict):
                    content = "\n".join(f"{k}: {v}" for k, v in item.items())
                elif isinstance(item, str):
                    content = item
                else:
                    content = json.dumps(item, indent=2)

                documents.append(Document(
                    content=content,
                    source=f"{self.name}:{i}",
                    metadata={"file": self.file_path, "index": i},
                ))

            logger.info("json_source_loaded", name=self.name, docs=len(documents))
            return documents
        except Exception as e:
            logger.error("json_source_load_failed", name=self.name, error=str(e))
            return []


class TextKnowledgeSource(KnowledgeSource):
    """Plain text knowledge source.

    Wraps existing text content as a knowledge source.
    """

    def __init__(
        self,
        name: str,
        content: str,
        description: str = "",
        chunk_size: int | None = None,
    ):
        super().__init__(name, description)
        self.content = content
        self.chunk_size = chunk_size

    async def load(self) -> list[Document]:
        """Load text content into documents."""
        if self.chunk_size and len(self.content) > self.chunk_size:
            chunks: list[str] = []
            start = 0
            while start < len(self.content):
                end = start + self.chunk_size
                chunks.append(self.content[start:end])
                start = end
            return [
                Document(
                    content=chunk,
                    source=f"{self.name}:{i}",
                    metadata={"chunk_index": i},
                )
                for i, chunk in enumerate(chunks)
            ]

        return [Document(content=self.content, source=self.name, metadata={})]


class VectorStore:
    """Simple in-memory vector store for document retrieval.

    Can be replaced with a production vector DB implementation.
    """

    def __init__(self):
        self._docs: list[Document] = []

    async def add_documents(self, documents: list[Document]) -> None:
        """Add documents to the store."""
        self._docs.extend(documents)

    async def search(self, query: str, limit: int = 5) -> list[Document]:
        """Search documents by query similarity."""
        if not self._docs:
            return []

        query_lower = query.lower()
        query_terms = set(query_lower.split())

        scored: list[tuple[float, Document]] = []
        for doc in self._docs:
            doc_lower = doc.content.lower()
            matches = sum(1 for term in query_terms if term in doc_lower)
            if matches > 0:
                score = matches / len(query_terms) if query_terms else 0
                scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, doc in scored[:limit]:
            doc.score = score
            results.append(doc)
        return results

    def clear(self) -> None:
        """Clear all documents."""
        self._docs = []


class KnowledgeManager:
    """Manage multiple knowledge sources with unified querying."""

    def __init__(self, vector_store: VectorStore | None = None):
        self.sources: dict[str, KnowledgeSource] = {}
        self.vector_store = vector_store or VectorStore()

    async def add_source(self, source: KnowledgeSource) -> None:
        """Add a knowledge source and load its documents."""
        self.sources[source.name] = source
        await source.ensure_loaded()
        await self.vector_store.add_documents(source._documents)
        logger.info("knowledge_source_added", name=source.name, docs=len(source._documents))

    async def remove_source(self, name: str) -> bool:
        """Remove a knowledge source."""
        if name in self.sources:
            del self.sources[name]
            await self._rebuild_index()
            logger.info("knowledge_source_removed", name=name)
            return True
        return False

    async def query(self, query: str, limit: int = 5) -> list[Document]:
        """Query all knowledge sources for relevant documents."""
        return await self.vector_store.search(query, limit)

    async def query_source(
        self, source_name: str, query: str, limit: int = 5,
    ) -> list[Document]:
        """Query a specific knowledge source."""
        source = self.sources.get(source_name)
        if not source:
            logger.warning("knowledge_source_not_found", name=source_name)
            return []
        return await source.query(query, limit)

    async def query_all(
        self, query: str, limit: int = 5,
    ) -> dict[str, list[Document]]:
        """Query all sources individually and return per-source results."""
        results: dict[str, list[Document]] = {}
        for name, source in self.sources.items():
            results[name] = await source.query(query, limit)
        return results

    async def _rebuild_index(self) -> None:
        """Rebuild the vector store index from all sources."""
        self.vector_store.clear()
        for source in self.sources.values():
            if not source._loaded:
                await source.ensure_loaded()
            await self.vector_store.add_documents(source._documents)

    def list_sources(self) -> list[str]:
        """List all registered source names."""
        return list(self.sources.keys())
