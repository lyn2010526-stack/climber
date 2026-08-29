"""Tests for metrics collector, middleware config, and health check."""


import pytest

from app.core.health_check import HealthChecker
from app.core.metrics_collector import CounterMetric, HistogramMetric, MetricsCollector
from app.core.middleware_config import MiddlewareConfigManager


class TestMetricsCollector:
    def test_counter_increment(self):
        counter = CounterMetric(name="test")
        counter.increment()
        assert counter.value == 1
        counter.increment(5)
        assert counter.value == 6

    def test_histogram_percentiles(self):
        hist = HistogramMetric(name="test")
        for i in range(100):
            hist.record(float(i))
        assert hist.count() == 100
        assert hist.avg() == 49.5
        assert 49.0 <= hist.p50() <= 51.0
        assert 93.0 <= hist.p95() <= 96.0

    @pytest.mark.asyncio
    async def test_collector_snapshot(self):
        collector = MetricsCollector()
        collector._increment_counter("test_counter")
        collector._record_histogram("test_hist", 100.0)
        collector._set_gauge("test_gauge", 42.0)

        snapshot = collector.snapshot()
        assert "test_counter" in snapshot["counters"]
        assert "test_hist" in snapshot["histograms"]
        assert snapshot["gauges"]["test_gauge"] == 42.0

    @pytest.mark.asyncio
    async def test_collector_reset(self):
        collector = MetricsCollector()
        collector._increment_counter("test")
        collector.reset()
        snapshot = collector.snapshot()
        assert len(snapshot["counters"]) == 0


class TestMiddlewareConfigManager:
    def test_register_and_list(self):
        manager = MiddlewareConfigManager()
        manager.register("test", "app.core.middleware.MiddlewareBase", enabled=True)
        configs = manager.list_configs()
        assert len(configs) == 1
        assert configs[0]["name"] == "test"

    def test_enable_disable(self):
        manager = MiddlewareConfigManager()
        manager.register("test", "app.core.middleware.MiddlewareBase")
        manager.disable("test")
        config = manager.get_config("test")
        assert config["enabled"] is False

    def test_unregister(self):
        manager = MiddlewareConfigManager()
        manager.register("test", "app.core.middleware.MiddlewareBase")
        manager.unregister("test")
        assert manager.get_config("test") is None

    def test_build_chain(self):
        manager = MiddlewareConfigManager()
        # Register with invalid class path - should be skipped
        manager.register("invalid", "nonexistent.Module.Class")
        chain = manager.build_chain()
        assert chain is not None


class TestHealthChecker:
    @pytest.mark.asyncio
    async def test_liveness(self):
        checker = HealthChecker()
        assert await checker.liveness() is True

    @pytest.mark.asyncio
    async def test_readiness(self):
        checker = HealthChecker()
        # Should not raise
        result = await checker.readiness()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_full_check(self):
        checker = HealthChecker()
        status = await checker.check()
        assert "status" in status
        assert "checks" in status
        assert status["status"] in ("ok", "degraded")
