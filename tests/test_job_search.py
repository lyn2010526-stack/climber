"""Tests for job search."""


from app.search.job_search import (
    JobIndexEntry,
    JobSearchEngine,
    JobSearchQuery,
)


class TestJobSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = JobSearchEngine()
        entry = JobIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = JobSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = JobSearchEngine()
        entry = JobIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = JobSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
