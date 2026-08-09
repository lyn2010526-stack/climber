#!/usr/bin/env python3
"""Regression guard - automatically runs core test suite and alerts on failure.

Monitors code quality by running targeted tests. On failure, generates
a detailed report with failure summary and optionally sends alerts.

Usage:
    python scripts/regression_guard.py
    python scripts/regression_guard.py --full
    python scripts/regression_guard.py --watch --interval 300
    python scripts/regression_guard.py --notify webhook_url
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = PROJECT_ROOT / "tests"
REPORTS_DIR = PROJECT_ROOT / "logs" / "regression"

DEFAULT_TEST_ARGS = [
    "pytest",
    "tests/",
    "-x",
    "--tb=short",
    "-q",
    "--no-header",
    "-m",
    "not slow and not e2e",
    "--timeout=60",
]

FULL_TEST_ARGS = [
    "pytest",
    "tests/",
    "--tb=short",
    "-q",
    "--no-header",
    "--timeout=120",
]

QUICK_SMOKE_TESTS = [
    "pytest",
    "tests/",
    "-x",
    "--tb=line",
    "-q",
    "--no-header",
    "-m",
    "unit",
    "--timeout=30",
    "-k",
    "test_health or test_config or test_smoke or test_basic",
]


@dataclass
class TestResult:
    name: str
    passed: bool
    duration_seconds: float
    total: int = 0
    failures: int = 0
    errors: int = 0
    skipped: int = 0
    output: str = ""
    failed_tests: list[str] = field(default_factory=list)


@dataclass
class RegressionReport:
    timestamp: str
    overall_passed: bool
    test_results: list[TestResult] = field(default_factory=list)
    total_duration: float = 0.0
    alert_sent: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "overall_passed": self.overall_passed,
            "total_duration_seconds": round(self.total_duration, 2),
            "alert_sent": self.alert_sent,
            "test_results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "duration_seconds": round(r.duration_seconds, 2),
                    "total": r.total,
                    "failures": r.failures,
                    "errors": r.errors,
                    "skipped": r.skipped,
                    "failed_tests": r.failed_tests,
                }
                for r in self.test_results
            ],
        }


def parse_pytest_output(output: str) -> dict[str, int]:
    result = {"total": 0, "failures": 0, "errors": 0, "skipped": 0}
    for line in output.split("\n"):
        if "passed" in line or "failed" in line or "error" in line:
            parts = line.replace(",", "").split()
            for i, part in enumerate(parts):
                if part.isdigit():
                    num = int(part)
                    if i + 1 < len(parts):
                        key = parts[i + 1].lower().rstrip("s")
                        if key in ("passed", "failed", "error", "skipped"):
                            if key == "passed":
                                result["total"] += num
                            elif key == "failed":
                                result["failures"] += num
                                result["total"] += num
                            elif key == "error":
                                result["errors"] += num
                                result["total"] += num
                            elif key == "skipped":
                                result["skipped"] += num
                                result["total"] += num
    return result


def extract_failed_tests(output: str) -> list[str]:
    failed = []
    for line in output.split("\n"):
        if line.startswith("FAILED "):
            failed.append(line.replace("FAILED ", "").strip())
        elif line.startswith("ERROR "):
            failed.append(line.replace("ERROR ", "").strip())
    return failed


def run_test_suite(name: str, args: list[str]) -> TestResult:
    start = time.monotonic()
    try:
        proc = subprocess.run(
            args,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        duration = time.monotonic() - start
        output = proc.stdout + proc.stderr
        stats = parse_pytest_output(output)
        failed_tests = extract_failed_tests(output)

        return TestResult(
            name=name,
            passed=proc.returncode == 0,
            duration_seconds=duration,
            total=stats["total"],
            failures=stats["failures"],
            errors=stats["errors"],
            skipped=stats["skipped"],
            output=output[-5000:],
            failed_tests=failed_tests,
        )
    except subprocess.TimeoutExpired:
        return TestResult(
            name=name,
            passed=False,
            duration_seconds=300,
            output="Test suite timed out after 300s",
        )
    except Exception as e:
        return TestResult(
            name=name,
            passed=False,
            duration_seconds=time.monotonic() - start,
            output=f"Error running tests: {e}",
        )


async def send_webhook_alert(webhook_url: str, report: RegressionReport) -> bool:
    try:
        import httpx

        payload = {
            "text": "REGRESSION DETECTED",
            "timestamp": report.timestamp,
            "failures": [
                {"name": r.name, "failed_tests": r.failed_tests}
                for r in report.test_results
                if not r.passed
            ],
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook_url, json=payload)
            return resp.status_code < 400
    except Exception:
        return False


async def send_slack_alert(webhook_url: str, report: RegressionReport) -> bool:
    try:
        import httpx

        failed_suites = [r for r in report.test_results if not r.passed]
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Regression Alert"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{report.timestamp}*\n{len(failed_suites)} test suite(s) failed",
                },
            },
        ]
        for suite in failed_suites:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{suite.name}*\n"
                    + "\n".join(f"  - {t}" for t in suite.failed_tests[:5]),
                },
            })

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook_url, json={"blocks": blocks})
            return resp.status_code == 200
    except Exception:
        return False


def save_report(report: RegressionReport) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"regression_{timestamp}.json"
    report_path.write_text(json.dumps(report.to_dict(), indent=2))

    latest_link = REPORTS_DIR / "latest.json"
    if latest_link.exists():
        latest_link.unlink()
    latest_link.write_text(json.dumps(report.to_dict(), indent=2))
    return report_path


def format_report_text(report: RegressionReport) -> str:
    lines = [
        f"Regression Guard Report - {report.timestamp}",
        f"Overall: {'PASS' if report.overall_passed else 'FAIL'}",
        f"Duration: {report.total_duration:.1f}s",
        "-" * 60,
    ]
    for result in report.test_results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(
            f"  [{status}] {result.name:20s} "
            f"({result.total} tests, {result.failures} failures, "
            f"{result.duration_seconds:.1f}s)"
        )
        if result.failed_tests:
            for test in result.failed_tests[:5]:
                lines.append(f"        - {test}")
    lines.append("-" * 60)
    return "\n".join(lines)


def detect_flaky_tests(report_history: list[Path]) -> list[str]:
    if len(report_history) < 3:
        return []

    test_pass_counts: dict[str, int] = {}
    for report_path in report_history[-10:]:
        try:
            data = json.loads(report_path.read_text())
            for suite in data.get("test_results", []):
                for test_name in suite.get("failed_tests", []):
                    test_pass_counts[test_name] = test_pass_counts.get(test_name, 0) + 1
        except (json.JSONDecodeError, OSError):
            continue

    return [name for name, count in test_pass_counts.items() if count >= 2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Regression Guard - Automated test runner")
    parser.add_argument("--full", action="store_true", help="Run full test suite")
    parser.add_argument("--smoke", action="store_true", help="Run smoke tests only")
    parser.add_argument(
        "--watch", action="store_true", help="Watch mode - run continuously"
    )
    parser.add_argument(
        "--interval", type=int, default=300, help="Watch interval in seconds"
    )
    parser.add_argument("--notify", type=str, help="Webhook URL for alerts")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--fail-fast", action="store_true", help="Stop on first failure"
    )
    return parser.parse_args()


async def run_guard(args: argparse.Namespace) -> RegressionReport:
    if args.smoke:
        suites = [("smoke", QUICK_SMOKE_TESTS)]
    elif args.full:
        suites = [("full", FULL_TEST_ARGS)]
    else:
        suites = [("core", DEFAULT_TEST_ARGS)]

    results = []
    for name, test_args in suites:
        result = run_test_suite(name, test_args)
        results.append(result)
        if args.fail_fast and not result.passed:
            break

    overall_passed = all(r.passed for r in results)
    total_duration = sum(r.duration_seconds for r in results)

    report = RegressionReport(
        timestamp=datetime.now(UTC).isoformat(),
        overall_passed=overall_passed,
        test_results=results,
        total_duration=total_duration,
    )

    save_report(report)

    if not overall_passed and args.notify:
        if "slack" in args.notify.lower():
            report.alert_sent = await send_slack_alert(args.notify, report)
        else:
            report.alert_sent = await send_webhook_alert(args.notify, report)

    return report


async def main() -> int:
    args = parse_args()

    if args.watch:
        while True:
            report = await run_guard(args)
            if args.json:
                print(json.dumps(report.to_dict(), indent=2))
            else:
                print(format_report_text(report))

            if not report.overall_passed and not args.notify:
                print("\nREGRESSION DETECTED - Check logs for details")

            await asyncio.sleep(args.interval)
    else:
        report = await run_guard(args)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            print(format_report_text(report))

        if not report.overall_passed:
            return 1
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
