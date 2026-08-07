"""Tests for analytics plugin."""


from app.plugins.analytics_plugin import (
    AnalyticsPluginManager,
    AnalyticsPluginManifest,
)


class TestAnalyticsPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = AnalyticsPluginManager()
        AnalyticsPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = AnalyticsPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = AnalyticsPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
