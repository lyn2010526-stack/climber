#!/usr/bin/env python3
"""High-concurrency performance benchmark for Agent Engine.

Tests 100/500/1000 concurrent connections against key API endpoints.
Measures latency distribution, throughput, and error rates.
"""

import asyncio
import json
import statistics
import subprocess
import sys
import time
from datetime import datetime

import httpx

BASE_URL = "http://127.0.0.1:8000"
RESULTS = {}
SESSION_ID: str | None = None


def section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def record(category, metric, value, unit=""):
    key = f"{category}/{metric}"
    RESULTS[key] = {"value": value, "unit": unit}
    print(f"  {metric}: {value}{unit}")


# ──────────────────────────────────────────────────────────────
# 1. Single Request Latency (Cold)
# ──────────────────────────────────────────────────────────────
async def benchmark_single_requests():
    section("1. Single Request Latency (cold start)")

    endpoints = [
        ("GET", "/health"),
        ("GET", "/api/v1/tasks?limit=50"),
        ("GET", "/api/v1/crews?limit=50"),
        ("GET", "/api/v1/sessions?limit=50"),
        ("GET", "/api/v1/settings"),
        ("GET", "/metrics"),
    ]

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        for method, path in endpoints:
            latencies = []
            for _ in range(5):
                start = time.perf_counter()
                try:
                    resp = await client.get(path)
                    resp.raise_for_status()
                except Exception as e:
                    print(f"  {method} {path}: ERROR - {e}")
                    break
                elapsed = (time.perf_counter() - start) * 1000
                latencies.append(elapsed)
            else:
                avg = statistics.mean(latencies)
                med = statistics.median(latencies)
                p95 = sorted(latencies)[int(len(latencies) * 0.95)]
                p99 = sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) > 1 else latencies[0]
                name = path.replace("/api/v1/", "").replace("?", "_q")
                record("single", f"{method} {name} avg", f"{avg:.1f}", "ms")
                record("single", f"{method} {name} median", f"{med:.1f}", "ms")
                record("single", f"{method} {name} p95", f"{p95:.1f}", "ms")
                record("single", f"{method} {name} p99", f"{p99:.1f}", "ms")


# ──────────────────────────────────────────────────────────────
# 2. Concurrent Load Tests (100/500/1000)
# ──────────────────────────────────────────────────────────────
async def make_request(client, sem, path, method="GET", body=None):
    async with sem:
        start = time.perf_counter()
        try:
            if method == "GET":
                resp = await client.get(path)
            else:
                resp = await client.post(path, json=body)
            status = resp.status_code
        except Exception:
            status = 0
        elapsed = (time.perf_counter() - start) * 1000
        return elapsed, status


async def benchmark_concurrency(concurrency, path="/health", total_requests=500):
    sem = asyncio.Semaphore(concurrency)
    limits = httpx.Limits(
        max_connections=concurrency + 50,
        max_keepalive_connections=concurrency,
        keepalive_expiry=30,
    )
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=120,
        limits=limits,
    ) as client:
        tasks = [make_request(client, sem, path) for _ in range(total_requests)]
        start = time.perf_counter()
        results = await asyncio.gather(*tasks)
        total_time = (time.perf_counter() - start) * 1000

    latencies = [r[0] for r in results if r[1] == 200]
    errors = sum(1 for r in results if r[1] != 200)
    error_details = {}
    for r in results:
        if r[1] != 200:
            error_details[r[1]] = error_details.get(r[1], 0) + 1

    if latencies:
        avg = statistics.mean(latencies)
        med = statistics.median(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        p99 = sorted(latencies)[int(len(latencies) * 0.99)]
        qps = len(latencies) / (total_time / 1000)
        min_lat = min(latencies)
        max_lat = max(latencies)
        stdev = statistics.stdev(latencies) if len(latencies) > 1 else 0

        record("concurrent", f"c={concurrency} avg", f"{avg:.1f}", "ms")
        record("concurrent", f"c={concurrency} median", f"{med:.1f}", "ms")
        record("concurrent", f"c={concurrency} p95", f"{p95:.1f}", "ms")
        record("concurrent", f"c={concurrency} p99", f"{p99:.1f}", "ms")
        record("concurrent", f"c={concurrency} min", f"{min_lat:.1f}", "ms")
        record("concurrent", f"c={concurrency} max", f"{max_lat:.1f}", "ms")
        record("concurrent", f"c={concurrency} stdev", f"{stdev:.1f}", "ms")
        record("concurrent", f"c={concurrency} QPS", f"{qps:.1f}", "req/s")
        record("concurrent", f"c={concurrency} total_time", f"{total_time:.0f}", "ms")
        record("concurrent", f"c={concurrency} success", len(latencies), "req")
        record("concurrent", f"c={concurrency} errors", errors, "")
        if error_details:
            for code, count in sorted(error_details.items()):
                record("concurrent", f"c={concurrency} err_{code}", count, "")
    else:
        print(f"  c={concurrency}: ALL FAILED")


async def benchmark_concurrent_all():
    section("2. Concurrent Load Tests (/health)")
    for conc in [100, 500, 1000]:
        await benchmark_concurrency(conc, "/health", 500)


# ──────────────────────────────────────────────────────────────
# 3. API Endpoint Concurrency Tests
# ──────────────────────────────────────────────────────────────
async def benchmark_api_concurrency():
    section("3. API Endpoint Concurrency (c=100)")

    endpoints = [
        ("GET", "/health"),
        ("GET", "/api/v1/tasks?limit=50"),
        ("GET", "/api/v1/sessions?limit=50"),
        ("GET", "/api/v1/settings"),
    ]

    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=60,
        limits=httpx.Limits(max_connections=150, max_keepalive_connections=100),
    ) as client:
        for _method, path in endpoints:
            sem = asyncio.Semaphore(100)
            tasks = [make_request(client, sem, path) for _ in range(200)]
            start = time.perf_counter()
            results = await asyncio.gather(*tasks)
            total_time = (time.perf_counter() - start) * 1000

            latencies = [r[0] for r in results if r[1] == 200]
            errors = sum(1 for r in results if r[1] != 200)

            if latencies:
                avg = statistics.mean(latencies)
                p95 = sorted(latencies)[int(len(latencies) * 0.95)]
                qps = len(latencies) / (total_time / 1000)
                name = path.replace("/api/v1/", "").replace("?", "_q")
                record("api_concurrent", f"{name} avg", f"{avg:.1f}", "ms")
                record("api_concurrent", f"{name} p95", f"{p95:.1f}", "ms")
                record("api_concurrent", f"{name} QPS", f"{qps:.1f}", "req/s")
                record("api_concurrent", f"{name} errors", errors, "")
            else:
                print(f"  {path}: ALL FAILED")


# ──────────────────────────────────────────────────────────────
# 4. Memory Usage Under Load
# ──────────────────────────────────────────────────────────────
def get_process_memory(pid):
    """Get RSS memory in MB for a process."""
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024
    except (FileNotFoundError, PermissionError):
        pass
    result = subprocess.run(
        ["ps", "-p", pid, "-o", "rss="],
        capture_output=True, text=True
    )
    try:
        return int(result.stdout.strip()) / 1024
    except ValueError:
        return 0


def benchmark_memory():
    section("4. Memory Usage")

    result = subprocess.run(
        ["pgrep", "-f", "uvicorn app.main:app"],
        capture_output=True, text=True
    )
    pids = result.stdout.strip().split("\n")
    if not pids or not pids[0]:
        result = subprocess.run(
            ["pgrep", "-f", "app.main:app"],
            capture_output=True, text=True
        )
        pids = result.stdout.strip().split("\n")

    if not pids or not pids[0]:
        print("  Could not find server PID")
        return

    main_pid = pids[0]
    print(f"  Server PID: {main_pid}")

    mem_before = get_process_memory(main_pid)
    record("memory", "baseline_rss", f"{mem_before:.1f}", "MB")

    async def stress():
        sem = asyncio.Semaphore(100)
        async with httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=60,
            limits=httpx.Limits(max_connections=150, max_keepalive_connections=100),
        ) as client:
            tasks = [make_request(client, sem, "/health") for _ in range(1000)]
            await asyncio.gather(*tasks)

    loop = asyncio.new_event_loop()
    loop.run_until_complete(stress())
    loop.close()

    mem_after = get_process_memory(main_pid)
    record("memory", "post_test_rss", f"{mem_after:.1f}", "MB")
    record("memory", "delta", f"{mem_after - mem_before:.1f}", "MB")

    with open("/proc/meminfo") as f:
        lines = f.readlines()
    mem_total = next((l for l in lines if "MemTotal" in l), "")
    mem_avail = next((l for l in lines if "MemAvailable" in l), "")
    if mem_total and mem_avail:
        total_kb = int(mem_total.split()[1])
        avail_kb = int(mem_avail.split()[1])
        record("memory", "system_used", f"{(total_kb - avail_kb) / 1024:.0f}", "MB")
        record("memory", "system_available", f"{avail_kb / 1024:.0f}", "MB")
        record("memory", "system_total", f"{total_kb / 1024:.0f}", "MB")


# ──────────────────────────────────────────────────────────────
# 5. Health Check Component Analysis
# ──────────────────────────────────────────────────────────────
async def benchmark_health_components():
    section("5. Health Check Component Analysis")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        # Measure health endpoint multiple times
        latencies = []
        for _ in range(10):
            start = time.perf_counter()
            resp = await client.get("/health")
            elapsed = (time.perf_counter() - start) * 1000
            if resp.status_code == 200:
                latencies.append(elapsed)
                data = resp.json()
                if _ == 0:
                    # Print component details on first request
                    for component, info in data.items():
                        if isinstance(info, dict):
                            lat = info.get("latency_ms") or info.get("response_time_ms")
                            if lat:
                                record("health_component", component, f"{lat:.1f}", "ms")
                            else:
                                record("health_component", component, str(info), "")
                        else:
                            record("health_component", component, str(info), "")

        if latencies:
            record("health", "avg", f"{statistics.mean(latencies):.1f}", "ms")
            record("health", "median", f"{statistics.median(latencies):.1f}", "ms")
            record("health", "p95", f"{sorted(latencies)[int(len(latencies) * 0.95)]:.1f}", "ms")
            record("health", "min", f"{min(latencies):.1f}", "ms")
            record("health", "max", f"{max(latencies):.1f}", "ms")


# ──────────────────────────────────────────────────────────────
# 6. Sustained Load Test
# ──────────────────────────────────────────────────────────────
async def benchmark_sustained_load():
    section("6. Sustained Load Test (100 concurrent, 5 rounds)")

    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=60,
        limits=httpx.Limits(max_connections=150, max_keepalive_connections=100),
    ) as client:
        for round_num in range(5):
            sem = asyncio.Semaphore(100)
            tasks = [make_request(client, sem, "/health") for _ in range(100)]
            start = time.perf_counter()
            results = await asyncio.gather(*tasks)
            (time.perf_counter() - start) * 1000

            latencies = [r[0] for r in results if r[1] == 200]
            errors = sum(1 for r in results if r[1] != 200)

            if latencies:
                avg = statistics.mean(latencies)
                p95 = sorted(latencies)[int(len(latencies) * 0.95)]
                record("sustained", f"round_{round_num+1}_avg", f"{avg:.1f}", "ms")
                record("sustained", f"round_{round_num+1}_p95", f"{p95:.1f}", "ms")
                record("sustained", f"round_{round_num+1}_errors", errors, "")


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────
async def async_main():
    await benchmark_single_requests()
    await benchmark_concurrent_all()
    await benchmark_api_concurrency()
    await benchmark_health_components()
    await benchmark_sustained_load()


def main():
    print("Agent Engine High-Concurrency Performance Benchmark")
    print(f"Target: {BASE_URL}")
    print(f"Time: {datetime.now().isoformat()}")
    print(f"Python: {sys.version}")

    asyncio.run(async_main())
    benchmark_memory()

    # Summary
    section("BENCHMARK SUMMARY")
    print(json.dumps(RESULTS, indent=2))

    # Save results
    output_path = "/workspace/agent-engine/benchmark_results_stress.json"
    with open(output_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "target": BASE_URL,
            "results": RESULTS,
        }, f, indent=2)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
