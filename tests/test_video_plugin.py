"""Tests for video plugin."""


from app.plugins.video_plugin import (
    VideoPluginManager,
    VideoPluginManifest,
)


class TestVideoPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = VideoPluginManager()
        VideoPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = VideoPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = VideoPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
