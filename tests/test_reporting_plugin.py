"""Tests for reporting plugin."""


from app.plugins.reporting_plugin import (
    ReportingPluginManager,
    ReportingPluginManifest,
)


class TestReportingPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = ReportingPluginManager()
        ReportingPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = ReportingPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = ReportingPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
