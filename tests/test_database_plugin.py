"""Tests for database plugin."""


from app.plugins.database_plugin import (
    DatabasePluginManager,
    DatabasePluginManifest,
)


class TestDatabasePluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = DatabasePluginManager()
        DatabasePluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = DatabasePluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = DatabasePluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
