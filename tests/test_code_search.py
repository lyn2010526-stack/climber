"""Tests for code search."""


from app.search.code_search import (
    CodeIndexEntry,
    CodeSearchEngine,
    CodeSearchQuery,
)


class TestCodeSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = CodeSearchEngine()
        entry = CodeIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = CodeSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = CodeSearchEngine()
        entry = CodeIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = CodeSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
