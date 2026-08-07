"""Tests for logging plugin."""


from app.plugins.logging_plugin import (
    LoggingPluginManager,
    LoggingPluginManifest,
)


class TestLoggingPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = LoggingPluginManager()
        LoggingPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = LoggingPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = LoggingPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
