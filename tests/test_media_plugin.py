"""Tests for media plugin."""


from app.plugins.media_plugin import (
    MediaPluginManager,
    MediaPluginManifest,
)


class TestMediaPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = MediaPluginManager()
        MediaPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = MediaPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = MediaPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
