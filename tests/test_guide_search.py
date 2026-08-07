"""Tests for guide search."""


from app.search.guide_search import (
    GuideIndexEntry,
    GuideSearchEngine,
    GuideSearchQuery,
)


class TestGuideSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = GuideSearchEngine()
        entry = GuideIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = GuideSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = GuideSearchEngine()
        entry = GuideIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = GuideSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
