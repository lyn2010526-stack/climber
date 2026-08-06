"""System monitoring and alerting.

Provides in-memory metric recording, rule-based alert evaluation, and
alert history for cpu_usage, memory_usage, error_rate and custom metrics.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import StrEnum

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class AlertLevel(StrEnum):
    """Severity level of an alert."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Operator(StrEnum):
    """Comparison operator used to evaluate a metric against a threshold."""

    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"


class AlertRule(BaseModel):
    """A rule that triggers an alert when a metric crosses a threshold."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    metric: str
    operator: Operator
    threshold: float
    level: AlertLevel
    message: str = ""
    enabled: bool = True


class AlertEvent(BaseModel):
    """A single alert that was triggered by a rule."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    rule_id: str
    metric: str
    current_value: float
    threshold: float
    level: AlertLevel
    message: str
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Monitor:
    """Records metrics and evaluates configured alert rules."""

    def __init__(self) -> None:
        self._rules: dict[str, AlertRule] = {}
        self._metrics: dict[str, float] = {}
        self._metric_tags: dict[str, dict[str, str]] = {}
        self._alerts: list[AlertEvent] = []
        self._logger = structlog.get_logger(__name__)
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register the built-in alert rules."""
        defaults = [
            AlertRule(metric="cpu_usage", operator=Operator.GT, threshold=80.0, level=AlertLevel.WARNING, message="CPU usage exceeded 80%"),
            AlertRule(metric="memory_usage", operator=Operator.GT, threshold=90.0, level=AlertLevel.CRITICAL, message="Memory usage exceeded 90%"),
            AlertRule(metric="error_rate", operator=Operator.GT, threshold=0.05, level=AlertLevel.WARNING, message="Error rate exceeded 5%"),
        ]
        for rule in defaults:
            self._rules[rule.id] = rule

    async def register_rule(self, rule: AlertRule) -> bool:
        """Register an alert rule, returning False if the rule id already exists."""
        if rule.id in self._rules:
            self._logger.warning("rule_already_registered", rule_id=rule.id)
            return False
        self._rules[rule.id] = rule
        self._logger.info("rule_registered", rule_id=rule.id, metric=rule.metric, operator=rule.operator.value, threshold=rule.threshold, level=rule.level.value)
        return True

    async def remove_rule(self, rule_id: str) -> bool:
        """Remove a registered alert rule, returning True if it existed."""
        if rule_id not in self._rules:
            self._logger.warning("rule_not_found", rule_id=rule_id)
            return False
        del self._rules[rule_id]
        self._logger.info("rule_removed", rule_id=rule_id)
        return True

    async def record_metric(self, name: str, value: float, tags: dict[str, str] | None = None) -> list[AlertEvent]:
        """Record a metric value and trigger rule evaluation for it."""
        self._metrics[name] = value
        if tags is not None:
            self._metric_tags[name] = tags
        events = await self.check(name, value)
        if events:
            self._alerts.extend(events)
            self._logger.warning("alerts_triggered", metric=name, count=len(events))
        return events

    async def check(self, metric: str, value: float) -> list[AlertEvent]:
        """Check all applicable rules for a metric and return triggered alerts."""
        triggered: list[AlertEvent] = []
        for rule in self._rules.values():
            if not rule.enabled or rule.metric != metric:
                continue
            if self._matches(rule.operator, value, rule.threshold):
                event = AlertEvent(
                    rule_id=rule.id,
                    metric=metric,
                    current_value=value,
                    threshold=rule.threshold,
                    level=rule.level,
                    message=rule.message,
                )
                triggered.append(event)
                self._logger.info("alert_triggered", rule_id=rule.id, metric=metric, value=value, threshold=rule.threshold, level=rule.level.value)
        return triggered

    def _matches(self, operator: Operator, value: float, threshold: float) -> bool:
        """Evaluate whether a value satisfies an operator against a threshold."""
        comparisons: dict[Operator, bool] = {
            Operator.GT: value > threshold,
            Operator.LT: value < threshold,
            Operator.GTE: value >= threshold,
            Operator.LTE: value <= threshold,
        }
        return comparisons.get(operator, False)

    async def get_alerts(self, level: AlertLevel | None = None, limit: int = 50) -> list[AlertEvent]:
        """Return recent alert history, optionally filtered by level."""
        filtered = [a for a in self._alerts if level is None or a.level == level]
        return filtered[-limit:]

    async def get_metrics(self) -> dict[str, float]:
        """Return the current value of all recorded metrics."""
        return dict(self._metrics)

    async def summary(self) -> dict[str, object]:
        """Return alert statistics by level and the most recent alert time."""
        by_level = {level: 0 for level in AlertLevel}
        latest: datetime | None = None
        for alert in self._alerts:
            by_level[alert.level] = by_level.get(alert.level, 0) + 1
            if latest is None or alert.triggered_at > latest:
                latest = alert.triggered_at
        return {
            "total": len(self._alerts),
            "by_level": {level.value: count for level, count in by_level.items()},
            "latest_alert_at": latest.isoformat() if latest else None,
            "rule_count": len(self._rules),
            "metric_count": len(self._metrics),
        }


_monitor_instance: Monitor | None = None


async def get_monitor() -> Monitor:
    """Return the process-wide Monitor singleton."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = Monitor()
    return _monitor_instance
