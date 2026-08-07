"""Tests for notification plugin."""


from app.plugins.notification_plugin import (
    NotificationPluginManager,
    NotificationPluginManifest,
)


class TestNotificationPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = NotificationPluginManager()
        NotificationPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = NotificationPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = NotificationPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
