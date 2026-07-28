"""Document processing and RAG pipeline."""

from __future__ import annotations

import uuid
from typing import Any


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


def process_upload(
    content: str,
    filename: str,
    chunk_size: int = 500,
) -> list[dict[str, Any]]:
    """Process an upload into chunks with metadata."""
    text_chunks = chunk_text(content, chunk_size=chunk_size)
    results = []
    for i, chunk in enumerate(text_chunks):
        results.append({
            "id": str(uuid.uuid4()),
            "text": chunk,
            "metadata": {
                "filename": filename,
                "chunk_index": i,
                "total_chunks": len(text_chunks),
            },
        })
    return results
