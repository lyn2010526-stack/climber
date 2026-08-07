"""Tests for user search."""


from app.search.user_search import (
    UserIndexEntry,
    UserSearchEngine,
    UserSearchQuery,
)


class TestUserSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = UserSearchEngine()
        entry = UserIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = UserSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = UserSearchEngine()
        entry = UserIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = UserSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
