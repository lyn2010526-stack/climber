"""Monitor: dashboard - Monitoring and observability."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from collections.abc import Callable
from typing import Any


class DashboardMetricType(StrEnum):
    """Metric type."""
    COUNTER = 'counter'
    GAUGE = 'gauge'
    HISTOGRAM = 'histogram'
    SUMMARY = 'summary'


class DashboardAlertSeverity(StrEnum):
    """Alert severity."""
    INFO = 'info'
    WARNING = 'warning'
    CRITICAL = 'critical'
    EMERGENCY = 'emergency'


@dataclass
class DashboardMetric:
    """Metric data point."""
    name: str = ''
    value: float = 0.0
    metric_type: str = 'gauge'
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DashboardAlert:
    """Alert."""
    id: str = ''
    name: str = ''
    severity: str = 'info'
    message: str = ''
    source: str = ''
    timestamp: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False


@dataclass
class DashboardHealthCheck:
    """Health check."""
    name: str = ''
    status: str = 'unknown'
    latency_ms: float = 0.0
    message: str = ''
    last_checked: datetime = field(default_factory=datetime.utcnow)


class DashboardMonitor:
    """Monitor."""

    def __init__(self):
        self._metrics: list[DashboardMetric] = []
        self._alerts: list[DashboardAlert] = []
        self._health_checks: dict[str, DashboardHealthCheck] = {}
        self._alert_rules: list[dict[str, Any]] = []

    def record_metric(self, metric: DashboardMetric) -> None:
        """Record metric."""
        self._metrics.append(metric)

    def get_metrics(
        self, name: str | None = None, since: datetime | None = None
    ) -> list[DashboardMetric]:
        """Get metrics."""
        metrics = self._metrics
        if name:
            metrics = [m for m in metrics if m.name == name]
        if since:
            metrics = [m for m in metrics if m.timestamp >= since]
        return metrics

    def create_alert(self, alert: DashboardAlert) -> None:
        """Create alert."""
        self._alerts.append(alert)

    def get_alerts(self, severity: str | None = None, acknowledged: bool | None = None) -> list[DashboardAlert]:
        """Get alerts."""
        alerts = self._alerts
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        return alerts

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge alert."""
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def register_health_check(self, name: str, check_fn: Callable) -> None:
        """Register health check."""
        self._health_checks[name] = DashboardHealthCheck(name=name)

    async def run_health_checks(self) -> dict[str, DashboardHealthCheck]:
        """Run all health checks."""
        results = {}
        for name, check in self._health_checks.items():
            start = time.time()
            try:
                if asyncio.iscoroutinefunction(check):
                    await check()
                else:
                    check()
                check.status = 'healthy'
            except Exception as e:
                check.status = 'unhealthy'
                check.message = str(e)
            check.latency_ms = (time.time() - start) * 1000
            check.last_checked = datetime.utcnow()
            results[name] = check
        return results

    def get_stats(self) -> dict[str, Any]:
        """Get monitor stats."""
        return {
            'total_metrics': len(self._metrics),
            'total_alerts': len(self._alerts),
            'unacknowledged_alerts': sum(1 for a in self._alerts if not a.acknowledged),
            'health_checks': len(self._health_checks),
        }
