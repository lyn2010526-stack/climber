#!/usr/bin/env python3
"""Concurrency benchmark for multi-worker gunicorn deployment.

Tests that multiple workers handle concurrent requests correctly.
"""

import asyncio
import statistics
import sys
import time

try:
    import httpx
except ImportError:
    print("httpx not installed, installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx


BASE_URL = "http://localhost:8000"
CONCURRENCY_LEVELS = [1, 5, 10, 20, 50]
REQUESTS_PER_LEVEL = 100


async def make_request(client: httpx.AsyncClient, endpoint: str = "/health") -> float:
    """Make a single request and return response time."""
    start = time.monotonic()
    try:
        response = await client.get(f"{BASE_URL}{endpoint}")
        response.raise_for_status()
    except Exception:
        return -1.0
    return time.monotonic() - start


async def run_concurrency_test(concurrency: int, total_requests: int) -> dict:
    """Run a concurrency test with the specified number of concurrent workers."""
    results = []
    errors = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        semaphore = asyncio.Semaphore(concurrency)

        async def bounded_request():
            async with semaphore:
                return await make_request(client)

        tasks = [bounded_request() for _ in range(total_requests)]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in raw_results:
            if isinstance(r, Exception) or r < 0:
                errors += 1
            else:
                results.append(r)

    return {
        "concurrency": concurrency,
        "total_requests": total_requests,
        "successful": len(results),
        "failed": errors,
        "avg_time": statistics.mean(results) if results else 0,
        "median_time": statistics.median(results) if results else 0,
        "p95_time": sorted(results)[int(len(results) * 0.95)] if results else 0,
        "max_time": max(results) if results else 0,
        "min_time": min(results) if results else 0,
        "total_time": sum(results) if results else 0,
        "requests_per_second": len(results) / sum(results) if results and sum(results) > 0 else 0,
    }


def print_results(results: list[dict]):
    """Print formatted benchmark results."""
    print("\n" + "=" * 80)
    print("MULTI-WORKER CONCURRENCY BENCHMARK RESULTS")
    print("=" * 80)
    print(f"{'Concurrency':>12} | {'Success':>7} | {'Failed':>6} | {'Avg(ms)':>8} | {'P95(ms)':>8} | {'Max(ms)':>8} | {'Req/s':>8}")
    print("-" * 80)

    for r in results:
        print(
            f"{r['concurrency']:>12} | "
            f"{r['successful']:>7} | "
            f"{r['failed']:>6} | "
            f"{r['avg_time']*1000:>8.2f} | "
            f"{r['p95_time']*1000:>8.2f} | "
            f"{r['max_time']*1000:>8.2f} | "
            f"{r['requests_per_second']:>8.2f}"
        )

    print("=" * 80)


async def main():
    """Run the full concurrency benchmark suite."""
    print(f"Testing multi-worker deployment at {BASE_URL}")
    print(f"Concurrency levels: {CONCURRENCY_LEVELS}")
    print(f"Requests per level: {REQUESTS_PER_LEVEL}")

    # Quick health check first
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(f"{BASE_URL}/health")
            print(f"\nHealth check: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Response: {data.get('status', 'unknown')}")
        except Exception as e:
            print(f"\nHealth check failed: {e}")
            print("Make sure the server is running on port 8000")
            return []

    all_results = []
    for concurrency in CONCURRENCY_LEVELS:
        print(f"\nTesting concurrency={concurrency}...")
        result = await run_concurrency_test(concurrency, REQUESTS_PER_LEVEL)
        all_results.append(result)
        print(f"  Done: {result['successful']}/{result['total_requests']} success, "
              f"avg={result['avg_time']*1000:.1f}ms, "
              f"rps={result['requests_per_second']:.1f}")

    print_results(all_results)
    return all_results


if __name__ == "__main__":
    asyncio.run(main())
