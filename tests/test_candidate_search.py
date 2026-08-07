"""Tests for candidate search."""


from app.search.candidate_search import (
    CandidateIndexEntry,
    CandidateSearchEngine,
    CandidateSearchQuery,
)


class TestCandidateSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = CandidateSearchEngine()
        entry = CandidateIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = CandidateSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = CandidateSearchEngine()
        entry = CandidateIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = CandidateSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
