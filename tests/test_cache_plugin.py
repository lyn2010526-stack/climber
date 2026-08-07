"""Tests for cache plugin."""


from app.plugins.cache_plugin import (
    CachePluginManager,
    CachePluginManifest,
)


class TestCachePluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = CachePluginManager()
        CachePluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = CachePluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = CachePluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
