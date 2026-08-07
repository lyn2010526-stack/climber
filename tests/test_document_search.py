"""Tests for document search."""


from app.search.document_search import (
    DocumentIndexEntry,
    DocumentSearchEngine,
    DocumentSearchQuery,
)


class TestDocumentSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = DocumentSearchEngine()
        entry = DocumentIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = DocumentSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = DocumentSearchEngine()
        entry = DocumentIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = DocumentSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
