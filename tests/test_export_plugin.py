"""Tests for export plugin."""


from app.plugins.export_plugin import (
    ExportPluginManager,
    ExportPluginManifest,
)


class TestExportPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = ExportPluginManager()
        ExportPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = ExportPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = ExportPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
