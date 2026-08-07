"""Tests for payment plugin."""


from app.plugins.payment_plugin import (
    PaymentPluginManager,
    PaymentPluginManifest,
)


class TestPaymentPluginManager:
    """Tests for plugin manager."""

    def test_register(self):
        manager = PaymentPluginManager()
        PaymentPluginManifest(name='test')
        assert manager.get('test') is None

    def test_list_plugins(self):
        manager = PaymentPluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_register_hook(self):
        manager = PaymentPluginManager()
        manager.register_hook('test_event', lambda d: d)
        results = manager.trigger_hook('test_event', 'data')
        assert len(results) == 1
