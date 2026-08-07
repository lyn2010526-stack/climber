"""Tests for security plugin."""


from app.plugins.security_plugin import (
    SecurityPluginManager,
    SecurityPluginManifest,
)


class TestSecurityPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = SecurityPluginManager()
        SecurityPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = SecurityPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = SecurityPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
