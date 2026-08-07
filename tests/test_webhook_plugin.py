"""Tests for webhook plugin."""


from app.plugins.webhook_plugin import (
    WebhookPluginManager,
    WebhookPluginManifest,
)


class TestWebhookPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = WebhookPluginManager()
        WebhookPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = WebhookPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = WebhookPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
