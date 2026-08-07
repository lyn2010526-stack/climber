"""Tests for reference search."""


from app.search.reference_search import (
    ReferenceIndexEntry,
    ReferenceSearchEngine,
    ReferenceSearchQuery,
)


class TestReferenceSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = ReferenceSearchEngine()
        entry = ReferenceIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = ReferenceSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = ReferenceSearchEngine()
        entry = ReferenceIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = ReferenceSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
