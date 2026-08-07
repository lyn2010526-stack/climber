"""Tests for translation plugin."""


from app.plugins.translation_plugin import (
    TranslationPluginManager,
    TranslationPluginManifest,
)


class TestTranslationPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = TranslationPluginManager()
        TranslationPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = TranslationPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = TranslationPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
