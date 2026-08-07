"""Tests for help search."""


from app.search.help_search import (
    HelpIndexEntry,
    HelpSearchEngine,
    HelpSearchQuery,
)


class TestHelpSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = HelpSearchEngine()
        entry = HelpIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = HelpSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = HelpSearchEngine()
        entry = HelpIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = HelpSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
