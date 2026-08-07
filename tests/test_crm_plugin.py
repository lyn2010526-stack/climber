"""Tests for crm plugin."""


from app.plugins.crm_plugin import (
    CrmPluginManager,
    CrmPluginManifest,
)


class TestCrmPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = CrmPluginManager()
        CrmPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = CrmPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = CrmPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
