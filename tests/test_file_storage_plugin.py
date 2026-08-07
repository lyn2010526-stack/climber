"""Tests for file_storage plugin."""


from app.plugins.file_storage_plugin import (
    FileStoragePluginManager,
    FileStoragePluginManifest,
)


class TestFileStoragePluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = FileStoragePluginManager()
        FileStoragePluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = FileStoragePluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = FileStoragePluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
