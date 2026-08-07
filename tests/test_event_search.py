"""Tests for event search."""


from app.search.event_search import (
    EventIndexEntry,
    EventSearchEngine,
    EventSearchQuery,
)


class TestEventSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = EventSearchEngine()
        entry = EventIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = EventSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = EventSearchEngine()
        entry = EventIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = EventSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
