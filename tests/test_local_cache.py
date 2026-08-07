"""Tests for local cache."""


from app.cache.local_cache import (
    LocalCache,
)


class TestLocalCache:
    """Tests for cache."""

    def test_set_and_get(self):
        cache = LocalCache()
        cache.set('key1', 'value1')
        assert cache.get('key1') == 'value1'

    def test_delete(self):
        cache = LocalCache()
        cache.set('key1', 'value1')
        assert cache.delete('key1') is True
        assert cache.get('key1') is None

    def test_clear(self):
        cache = LocalCache()
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')
        cache.clear()
        assert cache.get('key1') is None
        assert cache.get('key2') is None

    def test_stats(self):
        cache = LocalCache()
        cache.set('key1', 'value1')
        cache.get('key1')
        stats = cache.stats()
        assert stats['size'] == 1
        assert stats['hits'] == 1
