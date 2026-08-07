"""Tests for product search."""


from app.search.product_search import (
    ProductIndexEntry,
    ProductSearchEngine,
    ProductSearchQuery,
)


class TestProductSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = ProductSearchEngine()
        entry = ProductIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = ProductSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = ProductSearchEngine()
        entry = ProductIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = ProductSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
