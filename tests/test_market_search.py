"""Tests for market search."""


from app.search.market_search import (
    MarketIndexEntry,
    MarketSearchEngine,
    MarketSearchQuery,
)


class TestMarketSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = MarketSearchEngine()
        entry = MarketIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = MarketSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = MarketSearchEngine()
        entry = MarketIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = MarketSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
