"""Tests for debug search."""


from app.search.debug_search import (
    DebugIndexEntry,
    DebugSearchEngine,
    DebugSearchQuery,
)


class TestDebugSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = DebugSearchEngine()
        entry = DebugIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = DebugSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = DebugSearchEngine()
        entry = DebugIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = DebugSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
