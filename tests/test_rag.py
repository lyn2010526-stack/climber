"""Tests for RAG document processing."""

from __future__ import annotations

from app.tools.rag import chunk_text, process_upload


class TestChunkText:
    """Tests for chunk_text function."""

    def test_short_text_returns_single_chunk(self):
        text = "Hello world"
        result = chunk_text(text, chunk_size=500)
        assert result == ["Hello world"]

    def test_exact_chunk_size(self):
        text = "a" * 500
        result = chunk_text(text, chunk_size=500)
        assert len(result) == 1
        assert result[0] == text

    def test_longer_text_splits(self):
        text = "a" * 1000
        result = chunk_text(text, chunk_size=500)
        assert len(result) == 3

    def test_with_overlap(self):
        text = "a" * 1000
        result = chunk_text(text, chunk_size=500, overlap=100)
        assert len(result) == 3

    def test_empty_string(self):
        result = chunk_text("", chunk_size=500)
        assert result == [""]

    def test_custom_chunk_size(self):
        text = "a" * 2000
        result = chunk_text(text, chunk_size=300)
        assert len(result) >= 6

    def test_overlap_smaller_than_chunk(self):
        text = "a" * 1500
        result = chunk_text(text, chunk_size=500, overlap=100)
        assert len(result) == 4


class TestProcessUpload:
    """Tests for process_upload function."""

    def test_process_short_content(self):
        result = process_upload("Hello world", "test.txt")
        assert len(result) == 1
        assert result[0]["text"] == "Hello world"
        assert result[0]["metadata"]["filename"] == "test.txt"
        assert result[0]["metadata"]["chunk_index"] == 0
        assert result[0]["metadata"]["total_chunks"] == 1

    def test_process_long_content(self):
        content = "a" * 2000
        result = process_upload(content, "long.txt", chunk_size=500)
        assert len(result) > 1
        for i, chunk in enumerate(result):
            assert chunk["metadata"]["chunk_index"] == i
            assert chunk["metadata"]["total_chunks"] == len(result)
            assert chunk["metadata"]["filename"] == "long.txt"

    def test_process_generates_unique_ids(self):
        content = "a" * 2000
        result = process_upload(content, "test.txt", chunk_size=500)
        ids = [chunk["id"] for chunk in result]
        assert len(set(ids)) == len(ids)

    def test_process_empty_content(self):
        result = process_upload("", "empty.txt")
        assert len(result) == 1
        assert result[0]["text"] == ""

    def test_process_custom_chunk_size(self):
        content = "a" * 1000
        result = process_upload(content, "test.txt", chunk_size=200)
        assert len(result) > 1
