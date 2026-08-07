"""Tests for order search."""


from app.search.order_search import (
    OrderIndexEntry,
    OrderSearchEngine,
    OrderSearchQuery,
)


class TestOrderSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = OrderSearchEngine()
        entry = OrderIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = OrderSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = OrderSearchEngine()
        entry = OrderIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = OrderSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
