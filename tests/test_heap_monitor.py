"""Tests for heap monitor."""


from app.monitoring.heap_monitor import (
    HeapAlert,
    HeapMetric,
    HeapMonitor,
)


class TestHeapMonitor:
    """Tests for monitor."""

    def test_record_metric(self):
        monitor = HeapMonitor()
        metric = HeapMetric(name='cpu', value=50.0, metric_type='gauge')
        monitor.record_metric(metric)
        assert len(monitor._metrics) == 1

    def test_create_alert(self):
        monitor = HeapMonitor()
        alert = HeapAlert(name='high_cpu', severity='warning')
        monitor.create_alert(alert)
        assert len(monitor._alerts) == 1

    def test_acknowledge_alert(self):
        monitor = HeapMonitor()
        alert = HeapAlert(id='a1', name='test')
        monitor.create_alert(alert)
        assert monitor.acknowledge_alert('a1')

    def test_get_stats(self):
        monitor = HeapMonitor()
        stats = monitor.get_stats()
        assert 'total_metrics' in stats
