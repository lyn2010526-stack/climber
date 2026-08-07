"""Tests for log search."""


from app.search.log_search import (
    LogIndexEntry,
    LogSearchEngine,
    LogSearchQuery,
)


class TestLogSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = LogSearchEngine()
        entry = LogIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = LogSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = LogSearchEngine()
        entry = LogIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = LogSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
