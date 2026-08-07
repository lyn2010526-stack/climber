"""Tests for forms plugin."""


from app.plugins.forms_plugin import (
    FormsPluginManager,
    FormsPluginManifest,
)


class TestFormsPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = FormsPluginManager()
        FormsPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = FormsPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = FormsPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
