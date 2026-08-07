"""Tests for faq search."""


from app.search.faq_search import (
    FaqIndexEntry,
    FaqSearchEngine,
    FaqSearchQuery,
)


class TestFaqSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = FaqSearchEngine()
        entry = FaqIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = FaqSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = FaqSearchEngine()
        entry = FaqIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = FaqSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
