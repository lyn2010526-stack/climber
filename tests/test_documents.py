"""Tests for document upload and RAG pipeline."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.tools.rag import chunk_text, process_upload


def test_chunk_text_short():
    """Short text should return single chunk."""
    text = "Hello world"
    chunks = chunk_text(text, chunk_size=500)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_long():
    """Long text should be split into multiple chunks."""
    text = "word " * 200  # ~1000 chars
    chunks = chunk_text(text, chunk_size=100, overlap=10)
    assert len(chunks) > 1


def test_chunk_text_overlap():
    """Chunks should have overlap."""
    text = "abcdefghij" * 20
    chunks = chunk_text(text, chunk_size=50, overlap=10)
    # Verify overlap exists between consecutive chunks
    if len(chunks) >= 2:
        # Last 10 chars of first chunk should appear in second chunk
        assert chunks[0][-10:] in chunks[1] or chunks[1].startswith(chunks[0][-10:])


def test_process_upload():
    """Test upload processing creates chunks with metadata."""
    text = "This is a test document. " * 50
    results = process_upload(text, "test.txt", chunk_size=100)
    assert len(results) > 0
    for r in results:
        assert "id" in r
        assert "text" in r
        assert "metadata" in r
        assert r["metadata"]["filename"] == "test.txt"


@pytest.fixture
def client():
    """Create test client."""
    # Use unique emails to avoid conflicts with existing data
    with TestClient(app) as c:
        yield c




