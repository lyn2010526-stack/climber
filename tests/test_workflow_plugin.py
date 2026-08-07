"""Tests for workflow plugin."""


from app.plugins.workflow_plugin import (
    WorkflowPluginManager,
    WorkflowPluginManifest,
)


class TestWorkflowPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = WorkflowPluginManager()
        WorkflowPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = WorkflowPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = WorkflowPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
