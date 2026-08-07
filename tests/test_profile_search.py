"""Tests for profile search."""


from app.search.profile_search import (
    ProfileIndexEntry,
    ProfileSearchEngine,
    ProfileSearchQuery,
)


class TestProfileSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = ProfileSearchEngine()
        entry = ProfileIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = ProfileSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = ProfileSearchEngine()
        entry = ProfileIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = ProfileSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
