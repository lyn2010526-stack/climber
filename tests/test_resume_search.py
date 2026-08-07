"""Tests for resume search."""


from app.search.resume_search import (
    ResumeIndexEntry,
    ResumeSearchEngine,
    ResumeSearchQuery,
)


class TestResumeSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = ResumeSearchEngine()
        entry = ResumeIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = ResumeSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = ResumeSearchEngine()
        entry = ResumeIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = ResumeSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
