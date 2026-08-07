"""Tests for user plugin."""


from app.plugins.user_plugin import (
    UserPluginManager,
    UserPluginManifest,
)


class TestUserPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = UserPluginManager()
        UserPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = UserPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = UserPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
