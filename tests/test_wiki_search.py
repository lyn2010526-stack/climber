"""Tests for wiki search."""


from app.search.wiki_search import (
    WikiIndexEntry,
    WikiSearchEngine,
    WikiSearchQuery,
)


class TestWikiSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = WikiSearchEngine()
        entry = WikiIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = WikiSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = WikiSearchEngine()
        entry = WikiIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = WikiSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
