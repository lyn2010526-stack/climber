#!/usr/bin/env python3
"""Performance monitor for Agent Engine API.

Tracks API response times, memory usage trends (leak detection),
CPU utilization, and request throughput. Stores historical data
for trend analysis and alerting.

Usage:
    python scripts/performance_monitor.py
    python scripts/performance_monitor.py --duration 60
    python scripts/performance_monitor.py --interval 5 --endpoint /api/v1/sessions
    python scripts/performance_monitor.py --report
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

DEFAULT_API_URL = os.getenv("PERF_API_URL", "http://localhost:8000")
DEFAULT_INTERVAL = float(os.getenv("PERF_INTERVAL", "5.0"))
DEFAULT_DURATION = int(os.getenv("PERF_DURATION", "60"))
METRICS_DIR = Path(__file__).resolve().parent.parent / "logs" / "performance"

RESPONSE_TIME_WARN_MS = int(os.getenv("PERF_RT_WARN", "500"))
RESPONSE_TIME_CRIT_MS = int(os.getenv("PERF_RT_CRIT", "2000"))
CPU_WARN_PERCENT = int(os.getenv("PERF_CPU_WARN", "70"))
CPU_CRIT_PERCENT = int(os.getenv("PERF_CPU_CRIT", "90"))
MEMORY_GROWTH_WARN_MB = int(os.getenv("PERF_MEM_GROWTH_WARN", "50"))
MEMORY_GROWTH_CRIT_MB = int(os.getenv("PERF_MEM_GROWTH_CRIT", "200"))
LEAK_DETECTION_WINDOW = int(os.getenv("PERF_LEAK_WINDOW", "30"))


@dataclass
class APIMetric:
    endpoint: str
    timestamp: str
    response_time_ms: float
    status_code: int
    success: bool


@dataclass
class SystemMetric:
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    load_avg_1m: float = 0.0
    open_connections: int = 0


@dataclass
class PerformanceReport:
    timestamp: str
    duration_seconds: float
    api_metrics: list[APIMetric] = field(default_factory=list)
    system_metrics: list[SystemMetric] = field(default_factory=list)
    alerts: list[str] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "duration_seconds": self.duration_seconds,
            "alerts": self.alerts,
            "summary": self.summary,
            "api_metrics_count": len(self.api_metrics),
            "system_metrics_count": len(self.system_metrics),
        }


class APIMonitor:
    def __init__(self, base_url: str, endpoints: list[str] | None = None):
        self.base_url = base_url
        self.endpoints = endpoints or ["/health", "/metrics"]
        self.metrics: list[APIMetric] = []

    async def probe_endpoint(self, client: httpx.AsyncClient, endpoint: str) -> APIMetric:
        start = time.monotonic()
        try:
            resp = await client.get(f"{self.base_url}{endpoint}")
            latency_ms = (time.monotonic() - start) * 1000
            return APIMetric(
                endpoint=endpoint,
                timestamp=datetime.now(UTC).isoformat(),
                response_time_ms=latency_ms,
                status_code=resp.status_code,
                success=200 <= resp.status_code < 500,
            )
        except Exception:
            latency_ms = (time.monotonic() - start) * 1000
            return APIMetric(
                endpoint=endpoint,
                timestamp=datetime.now(UTC).isoformat(),
                response_time_ms=latency_ms,
                status_code=0,
                success=False,
            )

    async def probe_all(self) -> list[APIMetric]:
        async with httpx.AsyncClient(timeout=10) as client:
            tasks = [self.probe_endpoint(client, ep) for ep in self.endpoints]
            results = await asyncio.gather(*tasks)
        self.metrics.extend(results)
        return results


class SystemMonitor:
    def __init__(self):
        self.metrics: list[SystemMetric] = []
        self._memory_history: deque[float] = deque(maxlen=LEAK_DETECTION_WINDOW)

    def sample(self) -> SystemMetric:
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            load = os.getloadavg()[0] if hasattr(os, "getloadavg") else 0.0

            try:
                import psutil

                connections = len(psutil.net_connections())
            except (psutil.AccessDenied, Exception):
                connections = 0

            metric = SystemMetric(
                timestamp=datetime.now(UTC).isoformat(),
                cpu_percent=cpu,
                memory_percent=mem.percent,
                memory_used_mb=mem.used / (1024**2),
                memory_available_mb=mem.available / (1024**2),
                load_avg_1m=load,
                open_connections=connections,
            )
        except ImportError:
            metric = SystemMetric(
                timestamp=datetime.now(UTC).isoformat(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0,
            )

        self.metrics.append(metric)
        self._memory_history.append(metric.memory_used_mb)
        return metric

    def detect_memory_leak(self) -> tuple[bool, float]:
        if len(self._memory_history) < LEAK_DETECTION_WINDOW:
            return False, 0.0

        history = list(self._memory_history)
        first_half = history[: len(history) // 2]
        second_half = history[len(history) // 2 :]

        avg_first = statistics.mean(first_half)
        avg_second = statistics.mean(second_half)
        growth_mb = avg_second - avg_first

        if growth_mb >= MEMORY_GROWTH_CRIT_MB:
            return True, growth_mb
        if growth_mb >= MEMORY_GROWTH_WARN_MB:
            return True, growth_mb
        return False, growth_mb

    def detect_cpu_sustained_high(self, window: int = 10) -> bool:
        if len(self.metrics) < window:
            return False
        recent = self.metrics[-window:]
        return all(m.cpu_percent >= CPU_WARN_PERCENT for m in recent)


def analyze_performance(
    api_metrics: list[APIMetric],
    system_metrics: list[SystemMetric],
    leak_detected: bool,
    leak_growth_mb: float,
) -> dict[str, Any]:
    summary: dict[str, Any] = {"status": "healthy", "alerts": []}

    if api_metrics:
        latencies = [m.response_time_ms for m in api_metrics if m.success]
        if latencies:
            summary["api_latency"] = {
                "mean_ms": round(statistics.mean(latencies), 2),
                "median_ms": round(statistics.median(latencies), 2),
                "p95_ms": round(sorted(latencies)[int(len(latencies) * 0.95)], 2),
                "p99_ms": round(sorted(latencies)[int(len(latencies) * 0.99)], 2),
                "max_ms": round(max(latencies), 2),
                "min_ms": round(min(latencies), 2),
            }

            if latencies and max(latencies) >= RESPONSE_TIME_CRIT_MS:
                summary["alerts"].append(
                    f"API latency critical: {max(latencies):.0f}ms exceeds {RESPONSE_TIME_CRIT_MS}ms"
                )
            elif latencies and statistics.mean(latencies) >= RESPONSE_TIME_WARN_MS:
                summary["alerts"].append(
                    f"API latency high: {statistics.mean(latencies):.0f}ms exceeds {RESPONSE_TIME_WARN_MS}ms"
                )

        failed = [m for m in api_metrics if not m.success]
        if failed:
            summary["api_failures"] = len(failed)
            summary["alerts"].append(f"{len(failed)} API probe(s) failed")

    if system_metrics:
        cpu_values = [m.cpu_percent for m in system_metrics]
        mem_values = [m.memory_percent for m in system_metrics]

        summary["cpu"] = {
            "mean_percent": round(statistics.mean(cpu_values), 1),
            "max_percent": round(max(cpu_values), 1),
        }
        summary["memory"] = {
            "mean_percent": round(statistics.mean(mem_values), 1),
            "max_percent": round(max(mem_values), 1),
            "current_used_mb": round(system_metrics[-1].memory_used_mb, 1),
        }

        if max(cpu_values) >= CPU_CRIT_PERCENT:
            summary["alerts"].append(f"CPU critical: {max(cpu_values):.0f}%")
        elif statistics.mean(cpu_values) >= CPU_WARN_PERCENT:
            summary["alerts"].append(f"CPU high: {statistics.mean(cpu_values):.0f}%")

        if max(mem_values) >= 90:
            summary["alerts"].append(f"Memory critical: {max(mem_values):.0f}%")

    if leak_detected:
        summary["alerts"].append(
            f"Memory leak suspected: {leak_growth_mb:.1f}MB growth in window"
        )

    if summary["alerts"]:
        summary["status"] = "degraded" if len(summary["alerts"]) < 3 else "critical"

    return summary


def save_metrics(report: PerformanceReport) -> Path:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = METRICS_DIR / f"perf_{timestamp}.json"
    data = report.to_dict()
    data["api_metrics"] = [m.__dict__ for m in report.api_metrics]
    data["system_metrics"] = [m.__dict__ for m in report.system_metrics]
    path.write_text(json.dumps(data, indent=2))

    latest = METRICS_DIR / "latest.json"
    latest.write_text(json.dumps(data, indent=2))
    return path


def format_report_text(report: PerformanceReport) -> str:
    lines = [
        f"Performance Report - {report.timestamp}",
        f"Duration: {report.duration_seconds:.0f}s",
        f"Status: {report.summary.get('status', 'unknown').upper()}",
        "-" * 60,
    ]

    if "api_latency" in report.summary:
        lat = report.summary["api_latency"]
        lines.append(
            f"  API Latency: mean={lat['mean_ms']}ms, "
            f"p95={lat['p95_ms']}ms, p99={lat['p99_ms']}ms, max={lat['max_ms']}ms"
        )

    if "cpu" in report.summary:
        cpu = report.summary["cpu"]
        lines.append(f"  CPU: mean={cpu['mean_percent']}%, max={cpu['max_percent']}%")

    if "memory" in report.summary:
        mem = report.summary["memory"]
        lines.append(
            f"  Memory: mean={mem['mean_percent']}%, max={mem['max_percent']}%, "
            f"used={mem['current_used_mb']:.0f}MB"
        )

    if report.summary.get("alerts"):
        lines.append("")
        lines.append("  ALERTS:")
        for alert in report.summary["alerts"]:
            lines.append(f"    - {alert}")

    lines.append("-" * 60)
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Performance Monitor")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help="Sampling interval")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION, help="Total duration")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="API base URL")
    parser.add_argument(
        "--endpoint", action="append", help="Endpoints to probe (can repeat)"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    return parser.parse_args()


async def main() -> int:
    args = parse_args()

    api_monitor = APIMonitor(args.api_url, args.endpoint)
    sys_monitor = SystemMonitor()

    start_time = time.monotonic()
    iterations = int(args.duration / args.interval)

    for _ in range(iterations):
        await asyncio.gather(
            api_monitor.probe_all(),
            asyncio.to_thread(sys_monitor.sample),
        )
        await asyncio.sleep(args.interval)

    duration = time.monotonic() - start_time
    leak_detected, leak_growth = sys_monitor.detect_memory_leak()
    summary = analyze_performance(
        api_monitor.metrics, sys_monitor.metrics, leak_detected, leak_growth
    )

    report = PerformanceReport(
        timestamp=datetime.now(UTC).isoformat(),
        duration_seconds=duration,
        api_metrics=api_monitor.metrics,
        system_metrics=sys_monitor.metrics,
        alerts=summary.get("alerts", []),
        summary=summary,
    )

    save_metrics(report)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, default=str))
    else:
        print(format_report_text(report))

    if summary.get("status") == "critical":
        return 2
    if summary.get("status") == "degraded":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
