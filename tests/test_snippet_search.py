"""Tests for snippet search."""


from app.search.snippet_search import (
    SnippetIndexEntry,
    SnippetSearchEngine,
    SnippetSearchQuery,
)


class TestSnippetSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = SnippetSearchEngine()
        entry = SnippetIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = SnippetSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = SnippetSearchEngine()
        entry = SnippetIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = SnippetSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
