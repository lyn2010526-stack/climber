"""Comprehensive tests for all new modules (R9-R12)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.event_bus import EventBus
from app.core.health_check import HealthChecker
from app.core.metrics_collector import CounterMetric, HistogramMetric, MetricsCollector
from app.core.middleware import MiddlewareBase, MiddlewareChain
from app.core.middleware_config import MiddlewareConfigManager
from app.core.parallel_enhanced import EnhancedParallelToolExecutor

# ─── Middleware Base Tests ───────────────────────────────────────────────

class TestMiddlewareBase:
    def test_is_implemented_returns_false_for_base(self):
        mw = MiddlewareBase()
        assert mw.is_implemented("on_reasoning") is False
        assert mw.is_implemented("on_acting") is False
        assert mw.is_implemented("on_compress_context") is False
        assert mw.is_implemented("on_check_permission") is False
        assert mw.is_implemented("on_system_prompt") is False

    def test_is_implemented_returns_true_for_override(self):
        class CustomMiddleware(MiddlewareBase):
            async def on_reasoning(self, engine, session, input_kwargs, next_handler):
                yield

        mw = CustomMiddleware()
        assert mw.is_implemented("on_reasoning") is True
        assert mw.is_implemented("on_acting") is False


class TestMiddlewareChain:
    def test_empty_chain_properties(self):
        chain = MiddlewareChain([])
        assert chain.has_reasoning_middleware is False
        assert chain.has_acting_middleware is False
        assert chain.has_compress_middleware is False
        assert chain.has_permission_middleware is False
        assert chain.has_system_prompt_middleware is False

    @pytest.mark.asyncio
    async def test_system_prompt_pipeline(self):
        class UpperMiddleware(MiddlewareBase):
            async def on_system_prompt(self, engine, session, prompt):
                return prompt.upper()

        chain = MiddlewareChain([UpperMiddleware()])
        result = await chain.transform_system_prompt(MagicMock(), MagicMock(), "hello")
        assert result == "HELLO"

    @pytest.mark.asyncio
    async def test_multiple_middlewares_pipeline(self):
        class PrefixMiddleware(MiddlewareBase):
            async def on_system_prompt(self, engine, session, prompt):
                return f"[PREFIX]{prompt}"

        class SuffixMiddleware(MiddlewareBase):
            async def on_system_prompt(self, engine, session, prompt):
                return f"{prompt}[SUFFIX]"

        chain = MiddlewareChain([PrefixMiddleware(), SuffixMiddleware()])
        result = await chain.transform_system_prompt(MagicMock(), MagicMock(), "test")
        assert result == "[PREFIX]test[SUFFIX]"


# ─── Event Bus Tests ────────────────────────────────────────────────────

class TestEventBus:
    @pytest.mark.asyncio
    async def test_basic_publish_subscribe(self):
        bus = EventBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe("test", handler)
        await bus.publish("test", {"key": "value"})
        assert len(received) == 1
        assert received[0]["type"] == "test"

    @pytest.mark.asyncio
    async def test_global_subscriber(self):
        bus = EventBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe(None, handler)
        await bus.publish("a", {})
        await bus.publish("b", {})
        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_filter_function(self):
        bus = EventBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe("test", handler, filter_fn=lambda e: e.get("high"))
        await bus.publish("test", {"high": False})
        await bus.publish("test", {"high": True})
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        bus = EventBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe("test", handler)
        await bus.publish("test", {})
        assert len(received) == 1

        bus.unsubscribe("test", handler)
        await bus.publish("test", {})
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_history(self):
        bus = EventBus()
        await bus.publish("a", {"x": 1})
        await bus.publish("b", {"x": 2})

        assert len(bus.get_history()) == 2
        assert len(bus.get_history(event_type="a")) == 1

    @pytest.mark.asyncio
    async def test_history_limit(self):
        bus = EventBus(history_size=5)
        for i in range(10):
            await bus.publish("e", {"i": i})
        assert len(bus.get_history(limit=3)) == 3

    @pytest.mark.asyncio
    async def test_clear_history(self):
        bus = EventBus()
        await bus.publish("e", {})
        bus.clear_history()
        assert len(bus.get_history()) == 0


# ─── Metrics Collector Tests ────────────────────────────────────────────

class TestMetricsCollector:
    def test_counter(self):
        c = CounterMetric(name="test")
        c.increment()
        assert c.value == 1
        c.increment(10)
        assert c.value == 11

    def test_histogram(self):
        h = HistogramMetric(name="test")
        for i in range(50):
            h.record(float(i))
        assert h.count() == 50
        assert h.avg() == 24.5
        assert 24.0 <= h.p50() <= 26.0

    def test_histogram_empty(self):
        h = HistogramMetric(name="test")
        assert h.p50() == 0.0
        assert h.p95() == 0.0
        assert h.avg() == 0.0

    @pytest.mark.asyncio
    async def test_collector_snapshot(self):
        collector = MetricsCollector()
        collector._increment_counter("c1")
        collector._record_histogram("h1", 100.0)
        collector._set_gauge("g1", 42.0)

        snap = collector.snapshot()
        assert "counters" in snap
        assert "histograms" in snap
        assert "gauges" in snap
        assert snap["gauges"]["g1"] == 42.0

    @pytest.mark.asyncio
    async def test_collector_reset(self):
        collector = MetricsCollector()
        collector._increment_counter("c1")
        collector.reset()
        assert len(collector.snapshot()["counters"]) == 0


# ─── Middleware Config Manager Tests ─────────────────────────────────────

class TestMiddlewareConfigManager:
    def test_register_and_get(self):
        mgr = MiddlewareConfigManager()
        mgr.register("test", "app.core.middleware.MiddlewareBase")
        config = mgr.get_config("test")
        assert config is not None
        assert config["name"] == "test"

    def test_unregister(self):
        mgr = MiddlewareConfigManager()
        mgr.register("test", "app.core.middleware.MiddlewareBase")
        mgr.unregister("test")
        assert mgr.get_config("test") is None

    def test_enable_disable(self):
        mgr = MiddlewareConfigManager()
        mgr.register("test", "app.core.middleware.MiddlewareBase")
        mgr.disable("test")
        assert mgr.get_config("test")["enabled"] is False
        mgr.enable("test")
        assert mgr.get_config("test")["enabled"] is True

    def test_build_chain(self):
        mgr = MiddlewareConfigManager()
        mgr.register("invalid", "nonexistent.Module.Class")
        chain = mgr.build_chain()
        assert chain is not None

    def test_list_configs(self):
        mgr = MiddlewareConfigManager()
        mgr.register("a", "app.core.middleware.MiddlewareBase")
        mgr.register("b", "app.core.middleware.MiddlewareBase")
        configs = mgr.list_configs()
        assert len(configs) == 2


# ─── Health Checker Tests ───────────────────────────────────────────────

class TestHealthChecker:
    @pytest.mark.asyncio
    async def test_liveness(self):
        checker = HealthChecker()
        assert await checker.liveness() is True

    @pytest.mark.asyncio
    async def test_readiness(self):
        checker = HealthChecker()
        result = await checker.readiness()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_full_check(self):
        checker = HealthChecker()
        status = await checker.check()
        assert "status" in status
        assert "checks" in status
        assert "uptime_seconds" in status


# ─── Enhanced Parallel Executor Tests ───────────────────────────────────

class TestEnhancedParallelExecutor:
    @pytest.mark.asyncio
    async def test_execute_all_empty(self):
        registry = AsyncMock()
        executor = EnhancedParallelToolExecutor(registry)
        results = await executor.execute_all([])
        assert results == []

    @pytest.mark.asyncio
    async def test_concurrency_read_only(self):
        registry = AsyncMock()
        executor = EnhancedParallelToolExecutor(registry)
        limit = executor._get_concurrency_limit(["read_file", "grep", "glob"])
        assert limit == 20

    @pytest.mark.asyncio
    async def test_concurrency_mixed(self):
        registry = AsyncMock()
        executor = EnhancedParallelToolExecutor(registry)
        limit = executor._get_concurrency_limit(["read_file", "write_file"])
        assert limit == 3

    @pytest.mark.asyncio
    async def test_timeout_adaptive(self):
        registry = AsyncMock()
        executor = EnhancedParallelToolExecutor(registry, timeout_per_tool=30.0)
        assert executor._get_timeout_for_tool("run_command") == 90.0
        assert executor._get_timeout_for_tool("read_file") == 30.0

    @pytest.mark.asyncio
    async def test_event_bus_emission(self):
        registry = AsyncMock()
        event_bus = AsyncMock()
        session = MagicMock()
        session.session_id = "test"
        session._stop_requested = False

        executor = EnhancedParallelToolExecutor(
            registry, session=session, event_bus=event_bus,
        )
        tool_calls = [{"id": "c1", "function": {"name": "test_tool", "arguments": {}}}]
        await executor.execute_all(tool_calls)

        assert event_bus.publish.call_count >= 2
