"""Tests for storage plugin."""


from app.plugins.storage_plugin import (
    StoragePluginManager,
    StoragePluginManifest,
)


class TestStoragePluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = StoragePluginManager()
        StoragePluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = StoragePluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = StoragePluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
