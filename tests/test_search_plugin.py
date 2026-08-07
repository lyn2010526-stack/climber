"""Tests for search plugin."""


from app.plugins.search_plugin import (
    SearchPluginManager,
    SearchPluginManifest,
)


class TestSearchPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = SearchPluginManager()
        SearchPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = SearchPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = SearchPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
