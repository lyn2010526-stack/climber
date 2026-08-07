"""Tests for database monitor."""


from app.monitoring.database_monitor import (
    DatabaseAlert,
    DatabaseMetric,
    DatabaseMonitor,
)


class TestDatabaseMonitor:
    """Tests for monitor."""

    def test_record_metric(self):
        monitor = DatabaseMonitor()
        metric = DatabaseMetric(name='cpu', value=50.0, metric_type='gauge')
        monitor.record_metric(metric)
        assert len(monitor._metrics) == 1

    def test_create_alert(self):
        monitor = DatabaseMonitor()
        alert = DatabaseAlert(name='high_cpu', severity='warning')
        monitor.create_alert(alert)
        assert len(monitor._alerts) == 1

    def test_acknowledge_alert(self):
        monitor = DatabaseMonitor()
        alert = DatabaseAlert(id='a1', name='test')
        monitor.create_alert(alert)
        assert monitor.acknowledge_alert('a1')

    def test_get_stats(self):
        monitor = DatabaseMonitor()
        stats = monitor.get_stats()
        assert 'total_metrics' in stats
