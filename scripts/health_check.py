#!/usr/bin/env python3
"""Comprehensive health check for the Agent Engine platform.

Checks backend API health, database connectivity, Redis connectivity,
disk space, memory usage, and external service availability.

Usage:
    python scripts/health_check.py
    python scripts/health_check.py --json
    python scripts/health_check.py --interval 30  # continuous mode
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

DEFAULT_API_URL = os.getenv("HEALTH_API_URL", "http://localhost:8000")
DEFAULT_DB_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/climber.db")
DEFAULT_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DEFAULT_DISK_PATH = os.getenv("HEALTH_DISK_PATH", "/workspace/agent-engine")

DISK_WARNING_PERCENT = int(os.getenv("HEALTH_DISK_WARN", "80"))
DISK_CRITICAL_PERCENT = int(os.getenv("HEALTH_DISK_CRIT", "90"))
MEMORY_WARNING_PERCENT = int(os.getenv("HEALTH_MEM_WARN", "80"))
MEMORY_CRITICAL_PERCENT = int(os.getenv("HEALTH_MEM_CRIT", "90"))
API_TIMEOUT_SECONDS = float(os.getenv("HEALTH_API_TIMEOUT", "5.0"))


@dataclass
class CheckResult:
    name: str
    status: str  # "pass", "warn", "fail"
    message: str
    latency_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "latency_ms": round(self.latency_ms, 2),
            "details": self.details,
        }


@dataclass
class HealthReport:
    timestamp: str
    overall_status: str
    checks: list[CheckResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "overall_status": self.overall_status,
            "checks": [c.to_dict() for c in self.checks],
        }


async def check_api(url: str, timeout: float) -> CheckResult:
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{url}/health")
        latency = (time.monotonic() - start) * 1000
        if resp.status_code == 200:
            return CheckResult("api", "pass", "API is healthy", latency)
        if resp.status_code < 500:
            return CheckResult("api", "warn", f"API returned {resp.status_code}", latency)
        return CheckResult("api", "fail", f"API returned {resp.status_code}", latency)
    except httpx.ConnectError:
        latency = (time.monotonic() - start) * 1000
        return CheckResult("api", "fail", "Cannot connect to API", latency)
    except httpx.TimeoutException:
        latency = (time.monotonic() - start) * 1000
        return CheckResult("api", "fail", f"API timeout after {timeout}s", latency)
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return CheckResult("api", "fail", f"API error: {e}", latency)


async def check_database(db_url: str) -> CheckResult:
    start = time.monotonic()
    try:
        if db_url.startswith("sqlite"):
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import create_async_engine

            engine = create_async_engine(db_url)
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
            latency = (time.monotonic() - start) * 1000
            return CheckResult("database", "pass", "SQLite connection OK", latency)
        else:
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import create_async_engine

            engine = create_async_engine(db_url, pool_pre_ping=True)
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
            latency = (time.monotonic() - start) * 1000
            return CheckResult("database", "pass", "PostgreSQL connection OK", latency)
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return CheckResult("database", "fail", f"Database error: {e}", latency)


async def check_redis(redis_url: str) -> CheckResult:
    start = time.monotonic()
    try:
        from redis.asyncio import from_url

        client = from_url(redis_url, socket_connect_timeout=3, socket_timeout=3)
        pong = await client.ping()
        await client.close()
        latency = (time.monotonic() - start) * 1000
        if pong:
            return CheckResult("redis", "pass", "Redis connection OK", latency)
        return CheckResult("redis", "warn", "Redis ping returned False", latency)
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return CheckResult("redis", "fail", f"Redis error: {e}", latency)


def check_disk(path: str) -> CheckResult:
    start = time.monotonic()
    try:
        usage = shutil.disk_usage(path)
        total_gb = usage.total / (1024**3)
        used_gb = usage.used / (1024**3)
        free_gb = usage.free / (1024**3)
        percent_used = (usage.used / usage.total) * 100
        latency = (time.monotonic() - start) * 1000

        if percent_used >= DISK_CRITICAL_PERCENT:
            status = "fail"
            msg = f"Disk usage critical: {percent_used:.1f}% used ({free_gb:.1f} GB free)"
        elif percent_used >= DISK_WARNING_PERCENT:
            status = "warn"
            msg = f"Disk usage high: {percent_used:.1f}% used ({free_gb:.1f} GB free)"
        else:
            status = "pass"
            msg = f"Disk OK: {percent_used:.1f}% used ({free_gb:.1f} GB free)"

        return CheckResult(
            "disk",
            status,
            msg,
            latency,
            {
                "total_gb": round(total_gb, 2),
                "used_gb": round(used_gb, 2),
                "free_gb": round(free_gb, 2),
                "percent_used": round(percent_used, 1),
            },
        )
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return CheckResult("disk", "fail", f"Disk check error: {e}", latency)


def check_memory() -> CheckResult:
    start = time.monotonic()
    try:
        import psutil

        mem = psutil.virtual_memory()
        latency = (time.monotonic() - start) * 1000
        total_gb = mem.total / (1024**3)
        used_gb = mem.used / (1024**3)
        available_gb = mem.available / (1024**3)

        if mem.percent >= MEMORY_CRITICAL_PERCENT:
            status = "fail"
            msg = f"Memory critical: {mem.percent}% used ({available_gb:.1f} GB available)"
        elif mem.percent >= MEMORY_WARNING_PERCENT:
            status = "warn"
            msg = f"Memory high: {mem.percent}% used ({available_gb:.1f} GB available)"
        else:
            status = "pass"
            msg = f"Memory OK: {mem.percent}% used ({available_gb:.1f} GB available)"

        return CheckResult(
            "memory",
            status,
            msg,
            latency,
            {
                "total_gb": round(total_gb, 2),
                "used_gb": round(used_gb, 2),
                "available_gb": round(available_gb, 2),
                "percent_used": mem.percent,
            },
        )
    except ImportError:
        latency = (time.monotonic() - start) * 1000
        return CheckResult("memory", "warn", "psutil not installed, skipping", latency)
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return CheckResult("memory", "fail", f"Memory check error: {e}", latency)


def check_cpu() -> CheckResult:
    start = time.monotonic()
    try:
        import psutil

        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        latency = (time.monotonic() - start) * 1000

        if cpu_percent >= 90:
            status = "fail"
            msg = f"CPU critical: {cpu_percent}% utilization"
        elif cpu_percent >= 70:
            status = "warn"
            msg = f"CPU high: {cpu_percent}% utilization"
        else:
            status = "pass"
            msg = f"CPU OK: {cpu_percent}% utilization"

        return CheckResult(
            "cpu",
            status,
            msg,
            latency,
            {"percent_used": cpu_percent, "cpu_count": cpu_count},
        )
    except ImportError:
        latency = (time.monotonic() - start) * 1000
        return CheckResult("cpu", "warn", "psutil not installed, skipping", latency)
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return CheckResult("cpu", "fail", f"CPU check error: {e}", latency)


def check_open_file_descriptors() -> CheckResult:
    start = time.monotonic()
    try:
        import resource

        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        latency = (time.monotonic() - start) * 1000

        try:
            import psutil

            proc = psutil.Process()
            fd_count = proc.num_fds()
            percent = (fd_count / soft) * 100

            if percent >= 80:
                status = "warn"
                msg = f"FD usage high: {fd_count}/{soft} ({percent:.0f}%)"
            else:
                status = "pass"
                msg = f"FD OK: {fd_count}/{soft} ({percent:.0f}%)"

            return CheckResult(
                "file_descriptors",
                status,
                msg,
                latency,
                {"fd_count": fd_count, "fd_limit": soft, "percent": round(percent, 1)},
            )
        except ImportError:
            return CheckResult(
                "file_descriptors",
                "pass",
                f"FD limit: {soft}/{hard}",
                latency,
                {"fd_limit": soft, "fd_hard_limit": hard},
            )
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return CheckResult("file_descriptors", "warn", f"FD check error: {e}", latency)


async def run_all_checks(
    api_url: str = DEFAULT_API_URL,
    db_url: str = DEFAULT_DB_URL,
    redis_url: str = DEFAULT_REDIS_URL,
    disk_path: str = DEFAULT_DISK_PATH,
) -> HealthReport:
    api_result, db_result, redis_result = await asyncio.gather(
        check_api(api_url, API_TIMEOUT_SECONDS),
        check_database(db_url),
        check_redis(redis_url),
    )

    disk_result = check_disk(disk_path)
    mem_result = check_memory()
    cpu_result = check_cpu()
    fd_result = check_open_file_descriptors()

    checks = [api_result, db_result, redis_result, disk_result, mem_result, cpu_result, fd_result]

    if any(c.status == "fail" for c in checks):
        overall = "unhealthy"
    elif any(c.status == "warn" for c in checks):
        overall = "degraded"
    else:
        overall = "healthy"

    return HealthReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        overall_status=overall,
        checks=checks,
    )


def format_report_text(report: HealthReport) -> str:
    lines = [
        f"Health Check Report - {report.timestamp}",
        f"Overall Status: {report.overall_status.upper()}",
        "-" * 60,
    ]
    for check in report.checks:
        icon = {"pass": "[OK]", "warn": "[WARN]", "fail": "[FAIL]"}.get(check.status, "[?]")
        lines.append(f"  {icon} {check.name:20s} {check.message} ({check.latency_ms:.0f}ms)")
    lines.append("-" * 60)
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agent Engine health check")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--interval", type=int, default=0, help="Continuous mode interval (seconds)")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="API base URL")
    parser.add_argument("--db-url", default=DEFAULT_DB_URL, help="Database URL")
    parser.add_argument("--redis-url", default=DEFAULT_REDIS_URL, help="Redis URL")
    parser.add_argument("--disk-path", default=DEFAULT_DISK_PATH, help="Disk path to check")
    return parser.parse_args()


async def main() -> int:
    args = parse_args()

    if args.interval > 0:
        while True:
            report = await run_all_checks(args.api_url, args.db_url, args.redis_url, args.disk_path)
            if args.json:
                print(json.dumps(report.to_dict(), indent=2))
            else:
                print(format_report_text(report))
            await asyncio.sleep(args.interval)
    else:
        report = await run_all_checks(args.api_url, args.db_url, args.redis_url, args.disk_path)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            print(format_report_text(report))

        if report.overall_status == "unhealthy":
            return 2
        if report.overall_status == "degraded":
            return 1
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
