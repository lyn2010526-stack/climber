"""Tests for metric search."""


from app.search.metric_search import (
    MetricIndexEntry,
    MetricSearchEngine,
    MetricSearchQuery,
)


class TestMetricSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = MetricSearchEngine()
        entry = MetricIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = MetricSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = MetricSearchEngine()
        entry = MetricIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = MetricSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
