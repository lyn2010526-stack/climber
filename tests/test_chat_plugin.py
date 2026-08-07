"""Tests for chat plugin."""


from app.plugins.chat_plugin import (
    ChatPluginManager,
    ChatPluginManifest,
)


class TestChatPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = ChatPluginManager()
        ChatPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = ChatPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = ChatPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
