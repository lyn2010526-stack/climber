"""Tests for dashboard plugin."""


from app.plugins.dashboard_plugin import (
    DashboardPluginManager,
    DashboardPluginManifest,
)


class TestDashboardPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = DashboardPluginManager()
        DashboardPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = DashboardPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = DashboardPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
