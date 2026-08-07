"""Tests for import_data plugin."""


from app.plugins.import_data_plugin import (
    ImportDataPluginManager,
    ImportDataPluginManifest,
)


class TestImportDataPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = ImportDataPluginManager()
        ImportDataPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = ImportDataPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = ImportDataPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
