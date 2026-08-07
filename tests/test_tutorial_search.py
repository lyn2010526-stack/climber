"""Tests for tutorial search."""


from app.search.tutorial_search import (
    TutorialIndexEntry,
    TutorialSearchEngine,
    TutorialSearchQuery,
)


class TestTutorialSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = TutorialSearchEngine()
        entry = TutorialIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = TutorialSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = TutorialSearchEngine()
        entry = TutorialIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = TutorialSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
