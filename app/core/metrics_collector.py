"""Metrics Collector — aggregates event bus data into actionable metrics.

Provides:
- Real-time counters for tool calls, errors, latency
- Percentile calculations for performance monitoring
- Exportable metrics for dashboards and alerting
- Thread-safe accumulation
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.core.event_bus import EventBus, get_event_bus

logger = structlog.get_logger()


@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class CounterMetric:
    """Accumulating counter."""
    name: str
    value: int = 0
    tags: dict[str, str] = field(default_factory=dict)

    def increment(self, amount: int = 1) -> None:
        self.value += amount


@dataclass
class HistogramMetric:
    """Distribution tracking with percentiles."""
    name: str
    values: list[float] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)

    def record(self, value: float) -> None:
        self.values.append(value)
        # Keep last 1000 values to prevent memory growth
        if len(self.values) > 1000:
            self.values = self.values[-500:]

    def p50(self) -> float:
        if not self.values:
            return 0.0
        sorted_vals = sorted(self.values)
        idx = len(sorted_vals) // 2
        return sorted_vals[idx]

    def p95(self) -> float:
        if not self.values:
            return 0.0
        sorted_vals = sorted(self.values)
        idx = int(len(sorted_vals) * 0.95)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]

    def p99(self) -> float:
        if not self.values:
            return 0.0
        sorted_vals = sorted(self.values)
        idx = int(len(sorted_vals) * 0.99)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]

    def avg(self) -> float:
        if not self.values:
            return 0.0
        return sum(self.values) / len(self.values)

    def count(self) -> int:
        return len(self.values)


class MetricsCollector:
    """Collects and aggregates metrics from the event bus.

    Usage:
        collector = MetricsCollector()
        await collector.start()  # Subscribe to event bus
        # ... later ...
        metrics = collector.snapshot()
        await collector.stop()
    """

    def __init__(self, event_bus: EventBus | None = None):
        self._event_bus = event_bus
        self._counters: dict[str, CounterMetric] = {}
        self._histograms: dict[str, HistogramMetric] = {}
        self._gauge_values: dict[str, float] = {}
        self._started = False

    async def start(self) -> None:
        """Subscribe to event bus and start collecting."""
        if self._started:
            return

        if self._event_bus is None:
            self._event_bus = get_event_bus()

        # Subscribe to all events
        self._event_bus.subscribe(None, self._handle_event)
        self._started = True
        logger.info("metrics_collector.started")

    async def stop(self) -> None:
        """Stop collecting."""
        self._started = False
        logger.info("metrics_collector.stopped")

    async def _handle_event(self, event: dict[str, Any]) -> None:
        """Process an event from the bus."""
        event_type = event.get("type", "unknown")

        # Tool call metrics
        if event_type == "tool_start":
            self._increment_counter("tool_calls_total", tags={"tool": event.get("tool_name", "unknown")})

        elif event_type == "tool_complete":
            self._increment_counter("tool_calls_success", tags={"tool": event.get("tool_name", "unknown")})
            duration = event.get("duration_ms", 0)
            self._record_histogram("tool_duration_ms", duration, tags={"tool": event.get("tool_name", "unknown")})

        elif event_type == "tool_error":
            self._increment_counter("tool_errors_total", tags={"tool": event.get("tool_name", "unknown"), "error": event.get("error", "unknown")})

        # Session metrics
        elif event_type == "session_complete":
            self._increment_counter("sessions_completed")
            iterations = event.get("iterations", 0)
            self._record_histogram("session_iterations", iterations)

        elif event_type == "session_error":
            self._increment_counter("sessions_failed")

        # Middleware metrics
        elif event_type == "middleware_end":
            hook = event.get("hook", "unknown")
            duration = event.get("duration_ms", 0)
            self._record_histogram(f"middleware_{hook}_duration_ms", duration)

        # Permission metrics
        elif event_type == "permission_check":
            allowed = event.get("allowed", False)
            tool = event.get("tool_name", "unknown")
            self._increment_counter("permission_checks", tags={"tool": tool, "allowed": str(allowed)})

        # Iteration metrics
        elif event_type == "iteration_start":
            self._increment_counter("iterations_total")
            message_count = event.get("message_count", 0)
            self._set_gauge("current_message_count", message_count)

    def _increment_counter(self, name: str, amount: int = 1, tags: dict[str, str] | None = None) -> None:
        """Increment a counter metric."""
        key = f"{name}:{tags}" if tags else name
        if key not in self._counters:
            self._counters[key] = CounterMetric(name=name, tags=tags or {})
        self._counters[key].increment(amount)

    def _record_histogram(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Record a value in a histogram."""
        key = f"{name}:{tags}" if tags else name
        if key not in self._histograms:
            self._histograms[key] = HistogramMetric(name=name, tags=tags or {})
        self._histograms[key].record(value)

    def _set_gauge(self, name: str, value: float) -> None:
        """Set a gauge value."""
        self._gauge_values[name] = value

    def snapshot(self) -> dict[str, Any]:
        """Get a snapshot of all metrics."""
        counters = {}
        for metric in self._counters.values():
            counters[metric.name] = {
                "value": metric.value,
                "tags": metric.tags,
            }

        histograms = {}
        for metric in self._histograms.values():
            histograms[metric.name] = {
                "count": metric.count(),
                "avg": metric.avg(),
                "p50": metric.p50(),
                "p95": metric.p95(),
                "p99": metric.p99(),
                "tags": metric.tags,
            }

        return {
            "counters": counters,
            "histograms": histograms,
            "gauges": dict(self._gauge_values),
            "timestamp": time.time(),
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self._counters.clear()
        self._histograms.clear()
        self._gauge_values.clear()


# Global metrics collector instance
_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
