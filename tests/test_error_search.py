"""Tests for error search."""


from app.search.error_search import (
    ErrorIndexEntry,
    ErrorSearchEngine,
    ErrorSearchQuery,
)


class TestErrorSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = ErrorSearchEngine()
        entry = ErrorIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = ErrorSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = ErrorSearchEngine()
        entry = ErrorIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = ErrorSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
