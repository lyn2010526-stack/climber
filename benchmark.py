#!/usr/bin/env python3
"""Agent Engine Performance Benchmark Suite."""

import asyncio
import contextlib
import json
import os
import statistics
import subprocess
import time
from datetime import datetime

import httpx

BASE_URL = "http://127.0.0.1:8000"
RESULTS = {}


def section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def record(category, metric, value, unit=""):
    key = f"{category}/{metric}"
    RESULTS[key] = {"value": value, "unit": unit}
    print(f"  {metric}: {value}{unit}")


# ──────────────────────────────────────────────────────────────
# 1. API Response Time Tests
# ──────────────────────────────────────────────────────────────
async def benchmark_response_times():
    section("1. API Response Time (single request, cold)")

    endpoints = [
        ("GET", "/health", None),
        ("GET", "/api/v1/tasks?limit=50", None),
    ]

    # Also test agents list
    agents_endpoints = [
        ("GET", "/api/v1/crews?limit=50", None),
        ("GET", "/api/v1/sessions?limit=50", None),
        ("GET", "/api/v1/settings", None),
        ("GET", "/metrics", None),
    ]
    endpoints.extend(agents_endpoints)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        for method, path, body in endpoints:
            latencies = []
            # warm up
            with contextlib.suppress(Exception):
                await client.get(path) if method == "GET" else await client.post(path, json=body)
            # measure 5 times
            for _ in range(5):
                start = time.perf_counter()
                try:
                    if method == "GET":
                        resp = await client.get(path)
                    else:
                        resp = await client.post(path, json=body)
                    resp.raise_for_status()
                except Exception as e:
                    print(f"  {method} {path}: ERROR - {e}")
                    break
                elapsed = (time.perf_counter() - start) * 1000  # ms
                latencies.append(elapsed)
            else:
                avg = statistics.mean(latencies)
                med = statistics.median(latencies)
                p95 = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0]
                name = path.replace("/api/v1/", "").replace("?", "_q")
                record("response_time", f"{method} {name} (avg)", f"{avg:.1f}", "ms")
                record("response_time", f"{method} {name} (median)", f"{med:.1f}", "ms")
                record("response_time", f"{method} {name} (p95)", f"{p95:.1f}", "ms")


# ──────────────────────────────────────────────────────────────
# 2. Concurrent Request Tests
# ──────────────────────────────────────────────────────────────
async def make_request(client, sem, path):
    async with sem:
        start = time.perf_counter()
        try:
            resp = await client.get(path)
            status = resp.status_code
        except Exception:
            status = 0
        elapsed = (time.perf_counter() - start) * 1000
        return elapsed, status


async def benchmark_concurrent(concurrency, path="/health", total_requests=200):
    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60, limits=httpx.Limits(max_connections=concurrency+10)) as client:
        tasks = [make_request(client, sem, path) for _ in range(total_requests)]
        start = time.perf_counter()
        results = await asyncio.gather(*tasks)
        total_time = (time.perf_counter() - start) * 1000

    latencies = [r[0] for r in results if r[1] == 200]
    errors = sum(1 for r in results if r[1] != 200)

    if latencies:
        avg = statistics.mean(latencies)
        med = statistics.median(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        p99 = sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) > 1 else latencies[0]
        qps = len(latencies) / (total_time / 1000)

        record("concurrent", f"concurrency={concurrency} avg", f"{avg:.1f}", "ms")
        record("concurrent", f"concurrency={concurrency} median", f"{med:.1f}", "ms")
        record("concurrent", f"concurrency={concurrency} p95", f"{p95:.1f}", "ms")
        record("concurrent", f"concurrency={concurrency} p99", f"{p99:.1f}", "ms")
        record("concurrent", f"concurrency={concurrency} QPS", f"{qps:.1f}", "req/s")
        record("concurrent", f"concurrency={concurrency} total_time", f"{total_time:.0f}", "ms")
        record("concurrent", f"concurrency={concurrency} errors", errors, "")
    else:
        print(f"  concurrency={concurrency}: ALL FAILED")


async def benchmark_concurrent_all():
    section("2. Concurrent Requests (/health)")
    for conc in [10, 50, 100]:
        await benchmark_concurrent(conc, "/health", 200)


# ──────────────────────────────────────────────────────────────
# 3. Memory Usage
# ──────────────────────────────────────────────────────────────
def benchmark_memory():
    section("3. Memory Usage")

    # Get server PID
    result = subprocess.run(
        ["pgrep", "-f", "uvicorn app.main:app"],
        capture_output=True, text=True
    )
    pids = result.stdout.strip().split("\n")
    if not pids or not pids[0]:
        # try finding the python process
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

    # Memory before benchmark
    mem_before = get_process_memory(main_pid)
    record("memory", "startup_rss", f"{mem_before:.1f}", "MB")

    # Run concurrent load to stress memory
    async def stress():
        sem = asyncio.Semaphore(50)
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, limits=httpx.Limits(max_connections=60)) as client:
            tasks = [make_request(client, sem, "/health") for _ in range(500)]
            await asyncio.gather(*tasks)

    # Use a new event loop for stress since we're in async context
    loop = asyncio.new_event_loop()
    loop.run_until_complete(stress())
    loop.close()

    # Memory after benchmark
    mem_after = get_process_memory(main_pid)
    record("memory", "post_test_rss", f"{mem_after:.1f}", "MB")
    record("memory", "delta", f"{mem_after - mem_before:.1f}", "MB")

    # System memory
    with open("/proc/meminfo") as f:
        lines = f.readlines()
    mem_total = next((line for line in lines if "MemTotal" in line), "")
    mem_avail = next((line for line in lines if "MemAvailable" in line), "")
    if mem_total and mem_avail:
        total_kb = int(mem_total.split()[1])
        avail_kb = int(mem_avail.split()[1])
        used_kb = total_kb - avail_kb
        record("memory", "system_used", f"{used_kb / 1024:.0f}", "MB")
        record("memory", "system_available", f"{avail_kb / 1024:.0f}", "MB")
        record("memory", "system_total", f"{total_kb / 1024:.0f}", "MB")


def get_process_memory(pid):
    """Get RSS memory in MB for a process."""
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024  # KB -> MB
    except (FileNotFoundError, PermissionError):
        pass
    # Fallback: use ps
    result = subprocess.run(
        ["ps", "-p", pid, "-o", "rss="],
        capture_output=True, text=True
    )
    try:
        return int(result.stdout.strip()) / 1024
    except ValueError:
        return 0


# ──────────────────────────────────────────────────────────────
# 4. Database Query Performance
# ──────────────────────────────────────────────────────────────
async def benchmark_db_queries():
    section("4. Database Query Performance")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        # Test with different page sizes
        for limit in [10, 50, 100, 500]:
            path = f"/api/v1/tasks?limit={limit}"
            latencies = []
            for _ in range(3):
                start = time.perf_counter()
                resp = await client.get(path)
                elapsed = (time.perf_counter() - start) * 1000
                if resp.status_code == 200:
                    latencies.append(elapsed)
            if latencies:
                record("db_query", f"tasks_limit={limit}", f"{statistics.mean(latencies):.1f}", "ms")

        # Test sessions endpoint with different limits
        for limit in [10, 50, 100]:
            path = f"/api/v1/sessions?limit={limit}"
            latencies = []
            for _ in range(3):
                start = time.perf_counter()
                resp = await client.get(path)
                elapsed = (time.perf_counter() - start) * 1000
                if resp.status_code == 200:
                    latencies.append(elapsed)
            if latencies:
                record("db_query", f"sessions_limit={limit}", f"{statistics.mean(latencies):.1f}", "ms")

        # Test settings endpoint (likely cached)
        latencies = []
        for _ in range(10):
            start = time.perf_counter()
            resp = await client.get("/api/v1/settings")
            elapsed = (time.perf_counter() - start) * 1000
            if resp.status_code == 200:
                latencies.append(elapsed)
        if latencies:
            record("db_query", "settings (x10 avg)", f"{statistics.mean(latencies):.1f}", "ms")

        # Check DB file size
        db_files = []
        data_dir = "/workspace/agent-engine/data"
        if os.path.exists(data_dir):
            for f in os.listdir(data_dir):
                fp = os.path.join(data_dir, f)
                size_mb = os.path.getsize(fp) / (1024 * 1024)
                record("db_query", f"db_file_{f}_size", f"{size_mb:.2f}", "MB")
                db_files.append((f, size_mb))

        # Count records via API
        for endpoint in ["/api/v1/tasks?limit=1", "/api/v1/sessions?limit=1"]:
            resp = await client.get(endpoint)
            if resp.status_code == 200:
                data = resp.json()
                count = len(data) if isinstance(data, list) else "N/A"
                record("db_query", f"{endpoint.split('?')[0].split('/')[-1]}_count", count, "records")


# ──────────────────────────────────────────────────────────────
# 5. Frontend Build Time
# ──────────────────────────────────────────────────────────────
def benchmark_frontend_build():
    section("5. Frontend Build Time")

    frontend_dir = "/workspace/agent-engine/frontend-react"
    if not os.path.exists(frontend_dir):
        print("  frontend-react directory not found")
        return

    # Check if node_modules exists
    if not os.path.exists(os.path.join(frontend_dir, "node_modules")):
        print("  Installing frontend dependencies...")
        start = time.perf_counter()
        subprocess.run(
            ["npm", "install"],
            cwd=frontend_dir,
            capture_output=True,
            text=True,
            timeout=120
        )
        install_time = time.perf_counter() - start
        record("frontend", "npm_install_time", f"{install_time:.1f}", "s")

    # Clean previous build
    dist_dir = os.path.join(frontend_dir, "dist")
    if os.path.exists(dist_dir):
        subprocess.run(["rm", "-rf", dist_dir], cwd=frontend_dir)

    # Run build and measure
    print("  Running npm run build...")
    start = time.perf_counter()
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=frontend_dir,
        capture_output=True,
        text=True,
        timeout=180
    )
    build_time = time.perf_counter() - start

    record("frontend", "build_time", f"{build_time:.1f}", "s")

    if result.returncode != 0:
        print(f"  Build FAILED:\n{result.stderr[-500:]}")
    else:
        # Measure build output size
        if os.path.exists(dist_dir):
            total_size = 0
            file_count = 0
            for root, _dirs, files in os.walk(dist_dir):
                for f in files:
                    fp = os.path.join(root, f)
                    total_size += os.path.getsize(fp)
                    file_count += 1
            record("frontend", "dist_total_size", f"{total_size / (1024*1024):.2f}", "MB")
            record("frontend", "dist_file_count", file_count, "files")

            # Breakdown by type
            ext_sizes = {}
            for root, _dirs, files in os.walk(dist_dir):
                for f in files:
                    ext = os.path.splitext(f)[1] or "(no ext)"
                    fp = os.path.join(root, f)
                    ext_sizes[ext] = ext_sizes.get(ext, 0) + os.path.getsize(fp)
            for ext, size in sorted(ext_sizes.items(), key=lambda x: -x[1]):
                record("frontend", f"dist_{ext}", f"{size / 1024:.1f}", "KB")


# ──────────────────────────────────────────────────────────────
# 6. Health Check Deep Analysis
# ──────────────────────────────────────────────────────────────
async def benchmark_health_deep():
    section("6. Health Check Component Latency")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        resp = await client.get("/health")
        if resp.status_code == 200:
            data = resp.json()
            for component, info in data.items():
                if isinstance(info, dict) and "latency_ms" in info:
                    record("health", component, f"{info['latency_ms']:.1f}", "ms")


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────
async def async_main():
    await benchmark_response_times()
    await benchmark_concurrent_all()
    await benchmark_db_queries()
    await benchmark_health_deep()

def main():
    print("Agent Engine Performance Benchmark")
    print(f"Target: {BASE_URL}")
    print(f"Time: {datetime.now().isoformat()}")

    # Record baseline memory before async work
    result = subprocess.run(
        ["pgrep", "-f", "uvicorn app.main:app"],
        capture_output=True, text=True
    )
    pids = result.stdout.strip().split("\n")
    server_pid = pids[0] if pids and pids[0] else None
    mem_before = 0
    if server_pid:
        mem_before = get_process_memory(server_pid)

    asyncio.run(async_main())

    # Measure memory after async work
    if server_pid:
        mem_after = get_process_memory(server_pid)
        section("3. Memory Usage")
        record("memory", "baseline_rss", f"{mem_before:.1f}", "MB")
        record("memory", "post_test_rss", f"{mem_after:.1f}", "MB")
        record("memory", "delta", f"{mem_after - mem_before:.1f}", "MB")

    benchmark_frontend_build()

    # Summary
    section("BENCHMARK SUMMARY")
    print(json.dumps(RESULTS, indent=2))

    # Save results
    output_path = "/workspace/agent-engine/benchmark_results.json"
    with open(output_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "target": BASE_URL,
            "results": RESULTS,
        }, f, indent=2)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
