"""Tests for article search."""


from app.search.article_search import (
    ArticleIndexEntry,
    ArticleSearchEngine,
    ArticleSearchQuery,
)


class TestArticleSearchEngine:
    """Tests for search engine."""

    def test_index_and_search(self):
        engine = ArticleSearchEngine()
        entry = ArticleIndexEntry(id='1', title='Test Document', content='Hello World')
        engine.index(entry)

        query = ArticleSearchQuery(query='hello')
        result = engine.search(query)
        assert result.total == 1

    def test_remove(self):
        engine = ArticleSearchEngine()
        entry = ArticleIndexEntry(id='1', title='Test')
        engine.index(entry)
        assert engine.remove('1')

    def test_get_stats(self):
        engine = ArticleSearchEngine()
        stats = engine.get_stats()
        assert 'total_documents' in stats
