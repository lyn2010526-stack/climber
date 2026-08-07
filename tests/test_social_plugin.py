"""Tests for social plugin."""


from app.plugins.social_plugin import (
    SocialPluginManager,
    SocialPluginManifest,
)


class TestSocialPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = SocialPluginManager()
        SocialPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = SocialPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = SocialPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
