"""Tests for document upload and RAG pipeline."""

from __future__ import annotations

import uuid
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
    import uuid
    # Use unique emails to avoid conflicts with existing data
    with TestClient(app) as c:
        yield c


def test_upload_document_flow(client: TestClient):
    """Test: register -> upload document -> list -> search."""
    # Register
    resp = client.post('/api/v1/auth/register', params={'email': f'rag-{uuid.uuid4()}@test.com', 'password': 'pass123'})
    assert resp.status_code == 200, f"Register failed: {resp.text}"
    token = resp.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    # Upload text directly
    resp = client.post('/api/v1/documents/index-text', headers=headers,
                       data={'text': 'Python is a programming language. ' * 20,
                             'name': 'Python Intro'})
    print(f"Upload status: {resp.status_code}, body: {resp.text}")
    assert resp.status_code == 200, f"Upload failed: {resp.text}"
    data = resp.json()
    assert data['status'] in ('indexed', 'cached')
    if data['status'] == 'indexed':
        assert data['chunks'] > 0
    else:
        assert data['chunks'] == 0

    # List documents
    resp = client.get('/api/v1/documents/', headers=headers)
    print(f"List status: {resp.status_code}, body: {resp.text}")
    assert resp.status_code == 200, f"List failed: {resp.text}"
    docs = resp.json()
    assert len(docs) >= 1

    # Search documents
    resp = client.post('/api/v1/documents/search', headers=headers,
                       params={'query': 'Python programming', 'n_results': 3})
    print(f"Search status: {resp.status_code}, body: {resp.text}")
    assert resp.status_code == 200, f"Search failed: {resp.text}"
    results = resp.json()
    assert 'results' in results


def test_delete_document(client: TestClient):
    """Test document deletion."""
    resp = client.post('/api/v1/auth/register', params={'email': f'del-{uuid.uuid4()}@test.com', 'password': 'pass123'})
    token = resp.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    # Upload
    resp = client.post('/api/v1/documents/index-text', headers=headers,
                       data={'text': 'Some test content ' * 10, 'name': 'Test Doc'})
    doc_id = resp.json()['id']
    assert doc_id, f"Expected valid doc_id, got: {resp.json()}"

    # Delete
    resp = client.delete(f'/api/v1/documents/{doc_id}', headers=headers)
    assert resp.status_code == 200

    # Verify gone
    resp = client.get('/api/v1/documents/', headers=headers)
    assert all(d['id'] != doc_id for d in resp.json())
