"""Tests for calendar plugin."""


from app.plugins.calendar_plugin import (
    CalendarPluginManager,
    CalendarPluginManifest,
)


class TestCalendarPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = CalendarPluginManager()
        CalendarPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = CalendarPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = CalendarPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
