"""Tests for task plugin."""


from app.plugins.task_plugin import (
    TaskPluginManager,
    TaskPluginManifest,
)


class TestTaskPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = TaskPluginManager()
        TaskPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = TaskPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = TaskPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
