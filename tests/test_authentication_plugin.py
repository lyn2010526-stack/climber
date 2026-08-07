"""Tests for authentication plugin."""


from app.plugins.authentication_plugin import (
    AuthenticationPluginManager,
    AuthenticationPluginManifest,
)


class TestAuthenticationPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = AuthenticationPluginManager()
        AuthenticationPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = AuthenticationPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = AuthenticationPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
