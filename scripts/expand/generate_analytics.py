#!/usr/bin/env python3
"""Generate analytics and ML modules."""

from __future__ import annotations

from pathlib import Path

BASE = Path("/workspace/agent-engine")


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def gen_analytics(name: str, class_name: str) -> str:
    return f'''"""Analytics module: {name} - Data analysis and reporting."""

from __future__ import annotations

import json
import statistics
from datetime import datetime, timedelta
from typing import Any, Optional, Sequence
from collections import defaultdict
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger()


@dataclass
class {class_name}DataPoint:
    """Single data point for analysis."""
    timestamp: datetime
    value: float
    label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class {class_name}TimeSeries:
    """Time series data container."""
    name: str
    points: list[{class_name}DataPoint] = field(default_factory=list)
    unit: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_point(self, timestamp: datetime, value: float, label: str = "") -> None:
        """Add a data point."""
        self.points.append({class_name}DataPoint(timestamp=timestamp, value=value, label=label))

    @property
    def values(self) -> list[float]:
        """Get all values."""
        return [p.value for p in self.points]

    @property
    def timestamps(self) -> list[datetime]:
        """Get all timestamps."""
        return [p.timestamp for p in self.points]

    def slice(self, start: datetime, end: datetime) -> "{class_name}TimeSeries":
        """Get time range slice."""
        filtered = [p for p in self.points if start <= p.timestamp <= end]
        return {class_name}TimeSeries(name=self.name, points=filtered, unit=self.unit)

    def resample(self, interval: str) -> "{class_name}TimeSeries":
        """Resample to regular intervals."""
        if not self.points:
            return {class_name}TimeSeries(name=self.name, unit=self.unit)

        interval_seconds = {{"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "1d": 86400}}.get(interval, 3600)
        sorted_points = sorted(self.points, key=lambda p: p.timestamp)
        resampled = []

        bucket_start = sorted_points[0].timestamp
        bucket_values = []

        for point in sorted_points:
            if (point.timestamp - bucket_start).total_seconds() < interval_seconds:
                bucket_values.append(point.value)
            else:
                if bucket_values:
                    avg = sum(bucket_values) / len(bucket_values)
                    resampled.append({class_name}DataPoint(timestamp=bucket_start, value=avg))
                bucket_start = point.timestamp
                bucket_values = [point.value]

        if bucket_values:
            avg = sum(bucket_values) / len(bucket_values)
            resampled.append({class_name}DataPoint(timestamp=bucket_start, value=avg))

        return {class_name}TimeSeries(name=self.name, points=resampled, unit=self.unit)


@dataclass
class {class_name}Metric:
    """Calculated metric result."""
    name: str
    value: float
    unit: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    dimensions: dict[str, str] = field(default_factory=dict)


class {class_name}Calculator:
    """Statistical calculations."""

    @staticmethod
    def sum(values: Sequence[float]) -> float:
        return sum(values)

    @staticmethod
    def mean(values: Sequence[float]) -> float:
        return statistics.mean(values) if values else 0

    @staticmethod
    def median(values: Sequence[float]) -> float:
        return statistics.median(values) if values else 0

    @staticmethod
    def std_dev(values: Sequence[float]) -> float:
        return statistics.stdev(values) if len(values) > 1 else 0

    @staticmethod
    def variance(values: Sequence[float]) -> float:
        return statistics.variance(values) if len(values) > 1 else 0

    @staticmethod
    def min_val(values: Sequence[float]) -> float:
        return min(values) if values else 0

    @staticmethod
    def max_val(values: Sequence[float]) -> float:
        return max(values) if values else 0

    @staticmethod
    def percentile(values: Sequence[float], p: float) -> float:
        """Calculate percentile."""
        if not values:
            return 0
        sorted_vals = sorted(values)
        k = (len(sorted_vals) - 1) * (p / 100)
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_vals) else f
        return sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f])

    @staticmethod
    def count(values: Sequence[Any]) -> int:
        return len(values)

    @staticmethod
    def rate(values: Sequence[float], period_seconds: float) -> float:
        """Calculate rate per second."""
        return len(values) / period_seconds if period_seconds > 0 else 0

    @staticmethod
    def growth_rate(current: float, previous: float) -> float:
        """Calculate growth rate."""
        if previous == 0:
            return 0
        return ((current - previous) / previous) * 100


class {class_name}Aggregator:
    """Data aggregation engine."""

    def __init__(self):
        self._series: dict[str, {class_name}TimeSeries] = {{}}

    def add_series(self, series: {class_name}TimeSeries) -> None:
        """Add time series."""
        self._series[series.name] = series

    def get_series(self, name: str) -> {class_name}TimeSeries | None:
        """Get series by name."""
        return self._series.get(name)

    def aggregate(
        self,
        series_names: list[str],
        func: str = "sum",
        interval: str = "1h",
    ) -> {class_name}TimeSeries:
        """Aggregate multiple series."""
        all_points = []
        for name in series_names:
            series = self._series.get(name)
            if series:
                resampled = series.resample(interval)
                all_points.extend(resampled.points)

        if not all_points:
            return {class_name}TimeSeries(name="aggregated")

        all_points.sort(key=lambda p: p.timestamp)
        result = {class_name}TimeSeries(name=f"aggregated_{{func}}")

        # Group by timestamp and aggregate
        grouped: dict[datetime, list[float]] = defaultdict(list)
        for point in all_points:
            grouped[point.timestamp].append(point.value)

        for ts, values in sorted(grouped.items()):
            calc = {class_name}Calculator()
            agg_val = 0
            if func == "sum":
                agg_val = calc.sum(values)
            elif func == "mean":
                agg_val = calc.mean(values)
            elif func == "max":
                agg_val = calc.max_val(values)
            elif func == "min":
                agg_val = calc.min_val(values)
            elif func == "count":
                agg_val = len(values)
            result.points.append({class_name}DataPoint(timestamp=ts, value=agg_val))

        return result

    def compare(
        self,
        series_a: str,
        series_b: str,
        method: str = "difference",
    ) -> {class_name}TimeSeries:
        """Compare two series."""
        a = self._series.get(series_a)
        b = self._series.get(series_b)
        if not a or not b:
            return {class_name}TimeSeries(name="comparison")

        result = {class_name}TimeSeries(name=f"{{series_a}}_vs_{{series_b}}")
        b_dict = {{p.timestamp: p.value for p in b.points}}

        for point in a.points:
            b_val = b_dict.get(point.timestamp, 0)
            if method == "difference":
                val = point.value - b_val
            elif method == "ratio":
                val = point.value / b_val if b_val != 0 else 0
            elif method == "percent_change":
                val = ((point.value - b_val) / b_val * 100) if b_val != 0 else 0
            else:
                val = point.value - b_val
            result.points.append({class_name}DataPoint(timestamp=point.timestamp, value=val))

        return result


class {class_name}Detector:
    """Anomaly and pattern detection."""

    @staticmethod
    def detect_outliers(values: list[float], threshold: float = 2.0) -> list[int]:
        """Detect outliers using z-score."""
        if len(values) < 3:
            return []
        mean = statistics.mean(values)
        std = statistics.stdev(values)
        if std == 0:
            return []
        return [i for i, v in enumerate(values) if abs((v - mean) / std) > threshold]

    @staticmethod
    def detect_trend(values: list[float]) -> str:
        """Detect trend direction."""
        if len(values) < 3:
            return "insufficient_data"
        first_half = statistics.mean(values[:len(values) // 2])
        second_half = statistics.mean(values[len(values) // 2:])
        diff = second_half - first_half
        threshold = abs(first_half) * 0.05 if first_half != 0 else 0.1
        if diff > threshold:
            return "increasing"
        if diff < -threshold:
            return "decreasing"
        return "stable"

    @staticmethod
    def detect_seasonality(values: list[float], period: int = 7) -> dict[str, Any]:
        """Detect seasonal patterns."""
        if len(values) < period * 2:
            return {{"detected": False, "reason": "insufficient_data"}}
        period_averages = []
        for i in range(period):
            period_vals = values[i::period]
            if period_vals:
                period_averages.append(statistics.mean(period_vals))
        overall_mean = statistics.mean(values)
        variance_between = statistics.variance(period_averages) if len(period_averages) > 1 else 0
        variance_within = statistics.variance(values) if len(values) > 1 else 0
        ratio = variance_between / variance_within if variance_within > 0 else 0
        return {{
            "detected": ratio > 0.5,
            "period": period,
            "ratio": ratio,
            "period_averages": period_averages,
        }}

    @staticmethod
    def moving_average(values: list[float], window: int = 5) -> list[float]:
        """Calculate moving average."""
        if len(values) < window:
            return values
        result = []
        for i in range(len(values)):
            start = max(0, i - window + 1)
            window_vals = values[start:i + 1]
            result.append(sum(window_vals) / len(window_vals))
        return result

    @staticmethod
    def exponential_smoothing(values: list[float], alpha: float = 0.3) -> list[float]:
        """Apply exponential smoothing."""
        if not values:
            return []
        result = [values[0]]
        for i in range(1, len(values)):
            smoothed = alpha * values[i] + (1 - alpha) * result[-1]
            result.append(smoothed)
        return result


class {class_name}Forecaster:
    """Simple forecasting methods."""

    @staticmethod
    def naive_forecast(values: list[float], steps: int = 1) -> list[float]:
        """Naive forecast (last value)."""
        if not values:
            return [0] * steps
        return [values[-1]] * steps

    @staticmethod
    def moving_average_forecast(values: list[float], window: int = 3, steps: int = 1) -> list[float]:
        """Moving average forecast."""
        if len(values) < window:
            return [statistics.mean(values) if values else 0] * steps
        return [statistics.mean(values[-window:])] * steps

    @staticmethod
    def linear_trend_forecast(values: list[float], steps: int = 1) -> list[float]:
        """Linear trend extrapolation."""
        if len(values) < 2:
            return [values[-1] if values else 0] * steps
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = statistics.mean(values)
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator != 0 else 0
        intercept = y_mean - slope * x_mean
        return [intercept + slope * (n + i) for i in range(steps)]

    @staticmethod
    def exponential_smoothing_forecast(values: list[float], alpha: float = 0.3, steps: int = 1) -> list[float]:
        """Exponential smoothing forecast."""
        if not values:
            return [0] * steps
        smoothed = values[0]
        for v in values[1:]:
            smoothed = alpha * v + (1 - alpha) * smoothed
        return [smoothed] * steps


class {class_name}Report:
    """Report generation."""

    def __init__(self, title: str):
        self.title = title
        self.sections: list[dict[str, Any]] = []
        self.generated_at = datetime.utcnow()

    def add_section(self, title: str, data: Any, chart_type: str = "table") -> None:
        """Add report section."""
        self.sections.append({{
            "title": title,
            "data": data,
            "chart_type": chart_type,
        }})

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {{
            "title": self.title,
            "generated_at": self.generated_at.isoformat(),
            "sections": self.sections,
        }}

    def to_markdown(self) -> str:
        """Convert to markdown."""
        lines = [f"# {{self.title}}", "", f"Generated: {{self.generated_at.isoformat()}}", ""]
        for section in self.sections:
            lines.append(f"## {{section['title']}}")
            lines.append(f"```json\n{{json.dumps(section['data'], indent=2, default=str)}}\n```")
            lines.append("")
        return "\n".join(lines)
'''


def gen_analytics_test(name: str, class_name: str) -> str:
    return f'''"""Tests for {name} analytics module."""

import pytest
from datetime import datetime, timedelta

from app.analytics.{name}_analytics import (
    {class_name}DataPoint,
    {class_name}TimeSeries,
    {class_name}Calculator,
    {class_name}Aggregator,
    {class_name}Detector,
    {class_name}Forecaster,
    {class_name}Report,
)


class Test{class_name}DataPoint:
    """Tests for data point."""

    def test_creation(self):
        dp = {class_name}DataPoint(timestamp=datetime.utcnow(), value=42.0)
        assert dp.value == 42.0
        assert dp.label == ""


class Test{class_name}TimeSeries:
    """Tests for time series."""

    def test_add_point(self):
        ts = {class_name}TimeSeries(name="test")
        ts.add_point(datetime.utcnow(), 10.0)
        assert len(ts.points) == 1

    def test_values(self):
        ts = {class_name}TimeSeries(name="test")
        ts.add_point(datetime.utcnow(), 10.0)
        ts.add_point(datetime.utcnow(), 20.0)
        assert ts.values == [10.0, 20.0]

    def test_slice(self):
        ts = {class_name}TimeSeries(name="test")
        now = datetime.utcnow()
        ts.add_point(now - timedelta(hours=2), 10.0)
        ts.add_point(now, 20.0)
        sliced = ts.slice(now - timedelta(minutes=30), now)
        assert len(sliced.points) == 1

    def test_resample(self):
        ts = {class_name}TimeSeries(name="test")
        now = datetime.utcnow()
        for i in range(10):
            ts.add_point(now + timedelta(minutes=i), float(i))
        resampled = ts.resample("5m")
        assert len(resampled.points) > 0


class Test{class_name}Calculator:
    """Tests for calculator."""

    def test_sum(self):
        assert {class_name}Calculator.sum([1, 2, 3]) == 6

    def test_mean(self):
        assert {class_name}Calculator.mean([1, 2, 3]) == 2.0

    def test_median(self):
        assert {class_name}Calculator.median([1, 2, 3]) == 2

    def test_std_dev(self):
        result = {class_name}Calculator.std_dev([1, 2, 3, 4, 5])
        assert result > 0

    def test_min_max(self):
        assert {class_name}Calculator.min_val([3, 1, 2]) == 1
        assert {class_name}Calculator.max_val([3, 1, 2]) == 3

    def test_percentile(self):
        result = {class_name}Calculator.percentile([1, 2, 3, 4, 5], 50)
        assert result == 3

    def test_growth_rate(self):
        assert {class_name}Calculator.growth_rate(110, 100) == 10.0
        assert {class_name}Calculator.growth_rate(100, 0) == 0


class Test{class_name}Aggregator:
    """Tests for aggregator."""

    def test_add_and_get_series(self):
        agg = {class_name}Aggregator()
        ts = {class_name}TimeSeries(name="test")
        agg.add_series(ts)
        assert agg.get_series("test") is not None

    def test_aggregate_sum(self):
        agg = {class_name}Aggregator()
        ts1 = {class_name}TimeSeries(name="s1")
        ts2 = {class_name}TimeSeries(name="s2")
        ts1.add_point(datetime.utcnow(), 10)
        ts2.add_point(datetime.utcnow(), 20)
        agg.add_series(ts1)
        agg.add_series(ts2)
        result = agg.aggregate(["s1", "s2"], func="sum")
        assert len(result.points) > 0


class Test{class_name}Detector:
    """Tests for anomaly detection."""

    def test_detect_outliers(self):
        values = [1, 2, 3, 4, 5, 100]
        outliers = {class_name}Detector.detect_outliers(values)
        assert 5 in outliers

    def test_detect_increasing_trend(self):
        trend = {class_name}Detector.detect_trend([1, 2, 3, 4, 5])
        assert trend == "increasing"

    def test_detect_decreasing_trend(self):
        trend = {class_name}Detector.detect_trend([5, 4, 3, 2, 1])
        assert trend == "decreasing"

    def test_moving_average(self):
        result = {class_name}Detector.moving_average([1, 2, 3, 4, 5], window=3)
        assert len(result) == 5

    def test_exponential_smoothing(self):
        result = {class_name}Detector.exponential_smoothing([1, 2, 3, 4, 5])
        assert len(result) == 5


class Test{class_name}Forecaster:
    """Tests for forecasting."""

    def test_naive_forecast(self):
        result = {class_name}Forecaster.naive_forecast([1, 2, 3], steps=2)
        assert result == [3, 3]

    def test_moving_average_forecast(self):
        result = {class_name}Forecaster.moving_average_forecast([1, 2, 3, 4, 5], window=3, steps=1)
        assert result[0] == 4.0

    def test_linear_trend_forecast(self):
        result = {class_name}Forecaster.linear_trend_forecast([1, 2, 3, 4, 5], steps=2)
        assert len(result) == 2
        assert result[0] > 5


class Test{class_name}Report:
    """Tests for report generation."""

    def test_add_section(self):
        report = {class_name}Report("Test Report")
        report.add_section("Section 1", {{"key": "value"}})
        assert len(report.sections) == 1

    def test_to_dict(self):
        report = {class_name}Report("Test")
        report.add_section("S1", {{"k": "v"}})
        d = report.to_dict()
        assert d["title"] == "Test"
        assert len(d["sections"]) == 1

    def test_to_markdown(self):
        report = {class_name}Report("Test")
        report.add_section("Section", {{"key": "value"}})
        md = report.to_markdown()
        assert "# Test" in md
        assert "## Section" in md
'''


def main() -> None:
    all_files: dict[str, str] = {}

    analytics_modules = [
        ("usage", "Usage", "Usage analytics"),
        ("performance", "Performance", "Performance metrics"),
        ("revenue", "Revenue", "Revenue analytics"),
        ("engagement", "Engagement", "User engagement analytics"),
        ("retention", "Retention", "User retention analysis"),
        ("conversion", "Conversion", "Conversion funnel analysis"),
        ("funnel", "Funnel", "Funnel analytics"),
        ("cohort", "Cohort", "Cohort analysis"),
        ("ab_testing", "AbTesting", "A/B test analytics"),
        ("realtime", "Realtime", "Real-time analytics"),
        ("predictive", "Predictive", "Predictive analytics"),
        ("anomaly", "Anomaly", "Anomaly detection"),
        ("segmentation", "Segmentation", "User segmentation"),
        ("attribution", "Attribution", "Attribution modeling"),
        ("ltv", "Ltv", "Lifetime value analysis"),
        ("churn", "Churn", "Churn prediction"),
        ("nps", "Nps", "Net promoter score"),
        ("satisfaction", "Satisfaction", "Customer satisfaction"),
        ("heatmap", "Heatmap", "Heatmap analytics"),
        ("geospatial", "Geospatial", "Geospatial analytics"),
    ]

    print(f"Generating {len(analytics_modules)} analytics modules with tests...")

    for name, class_name, _desc in analytics_modules:
        content = gen_analytics(name, class_name)
        all_files[f"app/analytics/{name}_analytics.py"] = content

        test_content = gen_analytics_test(name, class_name)
        all_files[f"tests/test_{name}_analytics.py"] = test_content

    print(f"Writing {len(all_files)} files...")
    for path_str, content in all_files.items():
        write_file(BASE / path_str, content)

    print(f"Done! Generated {len(all_files)} files across {len(analytics_modules)} analytics modules.")


if __name__ == "__main__":
    main()
