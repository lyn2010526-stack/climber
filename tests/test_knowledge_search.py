"""Tests for knowledge search."""


from app.search.knowledge_search import (
    KnowledgeIndexEntry,
    KnowledgeSearchEngine,
    KnowledgeSearchQuery,
)


class TestKnowledgeSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = KnowledgeSearchEngine()
        entry = KnowledgeIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = KnowledgeSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = KnowledgeSearchEngine()
        entry = KnowledgeIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = KnowledgeSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
