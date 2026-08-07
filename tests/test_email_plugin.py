"""Tests for email plugin."""


from app.plugins.email_plugin import (
    EmailPluginManager,
    EmailPluginManifest,
)


class TestEmailPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = EmailPluginManager()
        EmailPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = EmailPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = EmailPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
