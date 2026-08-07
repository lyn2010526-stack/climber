"""Tests for error_rate monitor."""


from app.monitoring.error_rate_monitor import (
    ErrorRateAlert,
    ErrorRateMetric,
    ErrorRateMonitor,
)


class TestErrorRateMonitor:
    """Tests for monitor."""

    def test_record_metric(self):
        monitor = ErrorRateMonitor()
        metric = ErrorRateMetric(name='cpu', value=50.0, metric_type='gauge')
        monitor.record_metric(metric)
        assert len(monitor._metrics) == 1

    def test_create_alert(self):
        monitor = ErrorRateMonitor()
        alert = ErrorRateAlert(name='high_cpu', severity='warning')
        monitor.create_alert(alert)
        assert len(monitor._alerts) == 1

    def test_acknowledge_alert(self):
        monitor = ErrorRateMonitor()
        alert = ErrorRateAlert(id='a1', name='test')
        monitor.create_alert(alert)
        assert monitor.acknowledge_alert('a1')

    def test_get_stats(self):
        monitor = ErrorRateMonitor()
        stats = monitor.get_stats()
        assert 'total_metrics' in stats
