"""Continuous Test Daemon - watches files and runs tests on change."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from threading import Lock, Thread
from typing import Any

from watchdog.events import (
    FileSystemEvent,
    PatternMatchingEventHandler,
)
from watchdog.observers import Observer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
COVERAGE_DIR = PROJECT_ROOT / "htmlcov"
TEST_RESULTS_FILE = LOGS_DIR / "test_daemon_results.json"
ALERT_STATE_FILE = LOGS_DIR / "test_daemon_alert_state.json"

BACKEND_PATTERNS = ["*.py"]
FRONTEND_PATTERNS = ["*.ts", "*.tsx", "*.js", "*.jsx", "*.css", "*.scss"]
BACKEND_IGNORES = [
    "*.pyc",
    "__pycache__/*",
    ".git/*",
    "node_modules/*",
    "htmlcov/*",
    ".pytest_cache/*",
    ".ruff_cache/*",
    ".mypy_cache/*",
    "logs/*",
    "workspace/*",
    "data/*",
    "sessions/*",
]
FRONTEND_IGNORES = [
    "node_modules/*",
    "dist/*",
    "build/*",
    ".git/*",
    "coverage/*",
    "*.d.ts",
]


class TestResult:
    """Represents a single test run result."""

    def __init__(
        self,
        backend: bool,
        passed: bool,
        duration: float,
        output: str,
        test_count: int = 0,
        fail_count: int = 0,
    ):
        self.backend = backend
        self.passed = passed
        self.duration = duration
        self.output = output
        self.test_count = test_count
        self.fail_count = fail_count
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "passed": self.passed,
            "duration": round(self.duration, 2),
            "test_count": self.test_count,
            "fail_count": self.fail_count,
            "timestamp": self.timestamp,
        }


class AlertManager:
    """Manages test failure alerts."""

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self._state = self._load_state()

    def _load_state(self) -> dict[str, Any]:
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return {"last_alert_time": 0, "consecutive_failures": 0, "alerted_files": {}}

    def _save_state(self) -> None:
        self.state_file.write_text(json.dumps(self._state, indent=2))

    def should_alert(self, file_path: str) -> bool:
        """Check if we should send an alert for this file."""
        now = time.time()
        last_alert = self._state.get("alerted_files", {}).get(file_path, 0)
        return not now - last_alert < 300

    def record_failure(self, file_path: str) -> None:
        """Record a test failure."""
        now = time.time()
        self._state["consecutive_failures"] += 1
        if "alerted_files" not in self._state:
            self._state["alerted_files"] = {}
        self._state["alerted_files"][file_path] = now
        self._last_alert_time = now
        self._save_state()

    def record_success(self) -> None:
        """Reset consecutive failure count."""
        self._state["consecutive_failures"] = 0
        self._save_state()

    def send_alert(self, result: TestResult, trigger_file: str) -> None:
        """Send a test failure alert."""
        if not self.should_alert(trigger_file):
            return

        self.record_failure(trigger_file)
        consecutive = self._state["consecutive_failures"]

        border = "=" * 60
        print(f"\n{border}")
        print("TEST FAILURE ALERT")
        print(f"{border}")
        print(f"  Time:       {result.timestamp}")
        print(f"  Trigger:    {trigger_file}")
        print(f"  Backend:    {result.backend}")
        print(f"  Tests:      {result.test_count}")
        print(f"  Failures:   {result.fail_count}")
        print(f"  Duration:   {result.duration:.2f}s")
        print(f"  Consecutive failures: {consecutive}")
        print(f"{border}\n")

        if consecutive >= 3:
            print("WARNING: 3+ consecutive failures. Consider running full test suite.")
            print(f"  Run:  cd {PROJECT_ROOT} && python scripts/watch_tests.py --full\n")

        self._write_failure_log(result, trigger_file)

    def _write_failure_log(self, result: TestResult, trigger_file: str) -> None:
        """Write failure details to a log file."""
        failure_log = LOGS_DIR / "test_failures.log"
        with open(failure_log, "a") as f:
            f.write(f"\n{'=' * 60}\n")
            f.write(f"Time: {result.timestamp}\n")
            f.write(f"Trigger: {trigger_file}\n")
            f.write(f"Backend: {result.backend}\n")
            f.write(f"Duration: {result.duration:.2f}s\n")
            f.write(f"Tests: {result.test_count}, Failures: {result.fail_count}\n")
            f.write("\n--- Output ---\n")
            f.write(result.output[-2000:])
            f.write("\n")


class CoverageReporter:
    """Generates and tracks coverage reports."""

    def __init__(self, coverage_dir: Path):
        self.coverage_dir = coverage_dir
        self.history_file = LOGS_DIR / "coverage_history.json"
        self._history = self._load_history()

    def _load_history(self) -> list[dict[str, Any]]:
        if self.history_file.exists():
            try:
                return json.loads(self.history_file.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return []

    def _save_history(self) -> None:
        self.history_file.write_text(json.dumps(self._history[-50:], indent=2))

    def record_coverage(self, percentage: float) -> None:
        """Record a coverage measurement."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "coverage": percentage,
        }
        self._history.append(entry)
        self._save_history()

    def get_trend(self) -> str:
        """Get coverage trend direction."""
        if len(self._history) < 2:
            return "insufficient_data"
        recent = [e["coverage"] for e in self._history[-5:]]
        if recent[-1] > recent[0]:
            return "improving"
        elif recent[-1] < recent[0]:
            return "declining"
        return "stable"

    def parse_coverage_from_output(self, output: str) -> float | None:
        """Extract coverage percentage from pytest-cov output."""
        for line in output.split("\n"):
            if "TOTAL" in line and "%" in line:
                parts = line.split()
                for part in parts:
                    if part.endswith("%"):
                        try:
                            return float(part.rstrip("%"))
                        except ValueError:
                            pass
        return None


class TestRunner:
    """Runs tests and collects results."""

    def __init__(self):
        self.lock = Lock()
        self.last_backend_run = 0.0
        self.last_frontend_run = 0.0
        self.debounce_seconds = 2.0

    def run_backend_tests(
        self,
        target_file: str | None = None,
        quick: bool = True,
    ) -> TestResult:
        """Run backend pytest tests."""
        with self.lock:
            now = time.time()
            if now - self.last_backend_run < self.debounce_seconds:
                return TestResult(backend=True, passed=True, duration=0, output="debounced")
            self.last_backend_run = now

        start = time.time()

        if target_file and quick:
            test_file = self._find_matching_test(target_file)
            if test_file:
                cmd = [
                    sys.executable, "-m", "pytest",
                    str(test_file),
                    "-x", "-q", "--tb=line", "--no-header",
                    "-m", "not integration and not slow",
                ]
            else:
                cmd = [
                    sys.executable, "-m", "pytest",
                    "tests/", "-x", "-q", "--tb=line", "--no-header",
                    "-m", "not integration and not slow",
                ]
        else:
            cmd = [
                sys.executable, "-m", "pytest",
                "tests/", "-x", "--tb=short", "--no-header",
                "-m", "not integration and not slow",
            ]

        try:
            result = subprocess.run(
                cmd,
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=120,
            )
            duration = time.time() - start
            output = result.stdout + result.stderr
            test_count = self._parse_test_count(output)
            fail_count = self._parse_fail_count(output)

            return TestResult(
                backend=True,
                passed=result.returncode == 0,
                duration=duration,
                output=output,
                test_count=test_count,
                fail_count=fail_count,
            )
        except subprocess.TimeoutExpired:
            return TestResult(
                backend=True,
                passed=False,
                duration=time.time() - start,
                output="TIMEOUT: Backend tests exceeded 120s",
                test_count=0,
                fail_count=1,
            )
        except Exception as e:
            return TestResult(
                backend=True,
                passed=False,
                duration=time.time() - start,
                output=f"ERROR: {e}",
                test_count=0,
                fail_count=1,
            )

    def run_frontend_tests(self, quick: bool = True) -> TestResult:
        """Run frontend vitest tests."""
        with self.lock:
            now = time.time()
            if now - self.last_frontend_run < self.debounce_seconds:
                return TestResult(backend=False, passed=True, duration=0, output="debounced")
            self.last_frontend_run = now

        start = time.time()

        cmd = (
            ["npm", "test", "--", "--run", "--reporter=verbose"]
            if quick
            else ["npm", "test", "--", "--run"]
        )

        try:
            result = subprocess.run(
                cmd,
                cwd=str(PROJECT_ROOT / "frontend-react"),
                capture_output=True,
                text=True,
                timeout=120,
            )
            duration = time.time() - start
            output = result.stdout + result.stderr
            test_count = self._parse_vitest_count(output)
            fail_count = self._parse_vitest_fail_count(output)

            return TestResult(
                backend=False,
                passed=result.returncode == 0,
                duration=duration,
                output=output,
                test_count=test_count,
                fail_count=fail_count,
            )
        except subprocess.TimeoutExpired:
            return TestResult(
                backend=False,
                passed=False,
                duration=time.time() - start,
                output="TIMEOUT: Frontend tests exceeded 120s",
                test_count=0,
                fail_count=1,
            )
        except Exception as e:
            return TestResult(
                backend=False,
                passed=False,
                duration=time.time() - start,
                output=f"ERROR: {e}",
                test_count=0,
                fail_count=1,
            )

    def run_backend_coverage(self) -> TestResult:
        """Run full backend tests with coverage report."""
        start = time.time()
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/", "--cov=app",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--tb=short", "-q",
            "-m", "not integration and not slow",
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=300,
            )
            duration = time.time() - start
            output = result.stdout + result.stderr
            test_count = self._parse_test_count(output)
            fail_count = self._parse_fail_count(output)

            return TestResult(
                backend=True,
                passed=result.returncode == 0,
                duration=duration,
                output=output,
                test_count=test_count,
                fail_count=fail_count,
            )
        except subprocess.TimeoutExpired:
            return TestResult(
                backend=True,
                passed=False,
                duration=time.time() - start,
                output="TIMEOUT: Coverage run exceeded 300s",
                test_count=0,
                fail_count=1,
            )
        except Exception as e:
            return TestResult(
                backend=True,
                passed=False,
                duration=time.time() - start,
                output=f"ERROR: {e}",
                test_count=0,
                fail_count=1,
            )

    def run_e2e_tests(self) -> TestResult:
        """Run E2E tests."""
        start = time.time()
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/e2e/", "-v", "--tb=short",
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=180,
            )
            duration = time.time() - start
            output = result.stdout + result.stderr
            test_count = self._parse_test_count(output)
            fail_count = self._parse_fail_count(output)

            return TestResult(
                backend=True,
                passed=result.returncode == 0,
                duration=duration,
                output=output,
                test_count=test_count,
                fail_count=fail_count,
            )
        except subprocess.TimeoutExpired:
            return TestResult(
                backend=True,
                passed=False,
                duration=time.time() - start,
                output="TIMEOUT: E2E tests exceeded 180s",
                test_count=0,
                fail_count=1,
            )
        except Exception as e:
            return TestResult(
                backend=True,
                passed=False,
                duration=time.time() - start,
                output=f"ERROR: {e}",
                test_count=0,
                fail_count=1,
            )

    def _find_matching_test(self, source_file: str) -> Path | None:
        """Find the test file that matches a source file."""
        if not source_file.startswith("app/"):
            return None

        relative = Path(source_file)
        test_name = f"test_{relative.stem}.py"

        candidates = [
            PROJECT_ROOT / "tests" / test_name,
            PROJECT_ROOT / "tests" / relative.parent / test_name,
            PROJECT_ROOT / "tests" / "modules" / test_name,
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    @staticmethod
    def _parse_test_count(output: str) -> int:
        """Parse test count from pytest output."""
        import re
        match = re.search(r"(\d+?) passed", output)
        if match:
            return int(match.group(1))
        return 0

    @staticmethod
    def _parse_fail_count(output: str) -> int:
        """Parse failure count from pytest output."""
        import re
        match = re.search(r"(\d+?) failed", output)
        if match:
            return int(match.group(1))
        return 0

    @staticmethod
    def _parse_vitest_count(output: str) -> int:
        """Parse test count from vitest output."""
        import re
        match = re.search(r"(\d+?) passed", output)
        if match:
            return int(match.group(1))
        match = re.search(r"Tests\s+(\d+)", output)
        if match:
            return int(match.group(1))
        return 0

    @staticmethod
    def _parse_vitest_fail_count(output: str) -> int:
        """Parse failure count from vitest output."""
        import re
        match = re.search(r"(\d+?) failed", output)
        if match:
            return int(match.group(1))
        return 0


class ChangeHandler(PatternMatchingEventHandler):
    """Handles file system change events."""

    def __init__(
        self,
        runner: TestRunner,
        alert_manager: AlertManager,
        coverage_reporter: CoverageReporter,
    ):
        super().__init__(
            ignore_patterns=BACKEND_IGNORES,
            ignore_directories=True,
        )
        self.runner = runner
        self.alert_manager = alert_manager
        self.coverage_reporter = coverage_reporter
        self._pending_timer: Thread | None = None
        self._pending_func: callable | None = None
        self._lock = Lock()

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle_change(event.src_path)

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle_change(event.src_path)

    def _handle_change(self, file_path: str) -> None:
        """Route file change to appropriate test runner."""
        path = Path(file_path)

        if path.suffix == ".py":
            if "frontend-react" in file_path:
                return
            self._debounce(lambda: self._run_backend(file_path))
        elif path.suffix in (".ts", ".tsx", ".js", ".jsx"):
            if "frontend-react" not in file_path:
                return
            self._debounce(lambda: self._run_frontend(file_path))
        elif path.suffix == ".css":
            if "frontend-react" in file_path:
                self._debounce(lambda: self._run_frontend(file_path))

    def _debounce(self, func: callable) -> None:
        """Debounce rapid file changes."""
        with self._lock:
            self._pending_func = func
            if self._pending_timer is not None:
                self._pending_timer.join(timeout=0.1)
            thread = Thread(target=self._delayed_run, daemon=True)
            self._pending_timer = thread
            thread.start()

    def _delayed_run(self) -> None:
        """Wait for debounce period then execute pending function."""
        time.sleep(1.5)
        with self._lock:
            func = self._pending_func
            self._pending_func = None
            self._pending_timer = None
        if func is not None:
            func()

    def _run_backend(self, file_path: str) -> None:
        """Run backend tests for a changed file."""
        rel_path = os.path.relpath(file_path, str(PROJECT_ROOT))
        print(f"\n[BACKEND CHANGE] {rel_path}")
        print("  Running tests...")

        if "__pycache__" in file_path or ".pytest_cache" in file_path:
            return

        result = self.runner.run_backend_tests(target_file=file_path, quick=True)
        self._report_result(result, rel_path)

    def _run_frontend(self, file_path: str) -> None:
        """Run frontend tests for a changed file."""
        rel_path = os.path.relpath(file_path, str(PROJECT_ROOT))
        print(f"\n[FRONTEND CHANGE] {rel_path}")
        print("  Running tests...")

        if "node_modules" in file_path:
            return

        result = self.runner.run_frontend_tests(quick=True)
        self._report_result(result, rel_path)

    def _report_result(self, result: TestResult, trigger_file: str) -> None:
        """Report test results."""
        if result.output == "debounced":
            return

        status = "PASS" if result.passed else "FAIL"
        color = "\033[92m" if result.passed else "\033[91m"
        reset = "\033[0m"

        print(f"  {color}[{status}]{reset} {result.test_count} tests, "
              f"{result.fail_count} failures ({result.duration:.2f}s)")

        if result.passed:
            self.alert_manager.record_success()
        else:
            self.alert_manager.send_alert(result, trigger_file)
            print("\n  Failure output (last 15 lines):")
            lines = result.output.strip().split("\n")
            for line in lines[-15:]:
                print(f"    {line}")

        self._save_result(result, trigger_file)

    def _save_result(self, result: TestResult, trigger_file: str) -> None:
        """Persist result to JSON log."""
        results: list[dict[str, Any]] = []
        if TEST_RESULTS_FILE.exists():
            try:
                results = json.loads(TEST_RESULTS_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                results = []

        entry = result.to_dict()
        entry["trigger"] = trigger_file
        results.append(entry)
        results = results[-100:]
        TEST_RESULTS_FILE.write_text(json.dumps(results, indent=2))


class FrontendChangeHandler(PatternMatchingEventHandler):
    """Handles frontend-specific file changes."""

    def __init__(self, runner: TestRunner, alert_manager: AlertManager):
        super().__init__(
            patterns=FRONTEND_PATTERNS,
            ignore_patterns=FRONTEND_IGNORES,
            ignore_directories=True,
        )
        self.runner = runner
        self.alert_manager = alert_manager
        self._pending_timer: Thread | None = None
        self._pending_func: callable | None = None
        self._lock = Lock()

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        rel_path = os.path.relpath(event.src_path, str(PROJECT_ROOT))
        self._debounce(lambda: self._run_test(rel_path))

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        rel_path = os.path.relpath(event.src_path, str(PROJECT_ROOT))
        self._debounce(lambda: self._run_test(rel_path, is_new=True))

    def _debounce(self, func: callable) -> None:
        """Debounce rapid file changes."""
        with self._lock:
            self._pending_func = func
            if self._pending_timer is not None:
                self._pending_timer.join(timeout=0.1)
            thread = Thread(target=self._delayed_run, daemon=True)
            self._pending_timer = thread
            thread.start()

    def _delayed_run(self) -> None:
        """Wait for debounce period then execute pending function."""
        time.sleep(1.5)
        with self._lock:
            func = self._pending_func
            self._pending_func = None
            self._pending_timer = None
        if func is not None:
            func()

    def _run_test(self, rel_path: str, is_new: bool = False) -> None:
        """Run frontend tests."""
        label = "FRONTEND NEW" if is_new else "FRONTEND CHANGE"
        print(f"\n[{label}] {rel_path}")
        result = self.runner.run_frontend_tests(quick=True)
        self._report(result, rel_path)

    def _report(self, result: TestResult, trigger: str) -> None:
        if result.output == "debounced":
            return
        status = "PASS" if result.passed else "FAIL"
        color = "\033[92m" if result.passed else "\033[91m"
        reset = "\033[0m"
        print(f"  {color}[{status}]{reset} {result.test_count} tests, "
              f"{result.fail_count} failures ({result.duration:.2f}s)")
        if result.passed:
            self.alert_manager.record_success()
        else:
            self.alert_manager.send_alert(result, trigger)


class ContinuousTestDaemon:
    """Main daemon that orchestrates file watching and test execution."""

    def __init__(self):
        LOGS_DIR.mkdir(exist_ok=True)
        self.runner = TestRunner()
        self.alert_manager = AlertManager(ALERT_STATE_FILE)
        self.coverage_reporter = CoverageReporter(COVERAGE_DIR)
        self.observer = Observer()
        self._running = False

        self.backend_handler = ChangeHandler(
            self.runner, self.alert_manager, self.coverage_reporter,
        )
        self.frontend_handler = FrontendChangeHandler(
            self.runner, self.alert_manager,
        )

    def start(self) -> None:
        """Start the continuous test daemon."""
        self._running = True

        backend_path = str(PROJECT_ROOT)
        frontend_path = str(PROJECT_ROOT / "frontend-react" / "src")

        self.observer.schedule(self.backend_handler, backend_path, recursive=True)
        if Path(frontend_path).exists():
            self.observer.schedule(self.frontend_handler, frontend_path, recursive=True)

        self.observer.start()

        border = "=" * 60
        print(f"\n{border}")
        print("  CONTINUOUS TEST DAEMON")
        print(f"{border}")
        print(f"  Watching: {backend_path}")
        if Path(frontend_path).exists():
            print(f"  Watching: {frontend_path}")
        print(f"  Results:  {TEST_RESULTS_FILE}")
        print(f"  Alerts:   {LOGS_DIR / 'test_failures.log'}")
        print(f"  Coverage: {COVERAGE_DIR}")
        print(f"{border}")
        print("  Press Ctrl+C to stop\n")

        self._run_initial_tests()
        self._run_loop()

    def _run_initial_tests(self) -> None:
        """Run initial test pass on startup."""
        print("[INIT] Running initial test pass...")
        result = self.runner.run_backend_tests(quick=True)
        status = "PASS" if result.passed else "FAIL"
        print(f"  Backend: [{status}] {result.test_count} tests ({result.duration:.2f}s)")

    def _run_loop(self) -> None:
        """Main loop - runs periodic full tests and coverage."""
        cycle = 0
        while self._running:
            try:
                time.sleep(10)
                cycle += 1

                if cycle % 6 == 0:
                    self._run_periodic_backend()

                if cycle % 30 == 0:
                    self._run_periodic_coverage()

                if cycle % 60 == 0:
                    self._run_periodic_e2e()

            except KeyboardInterrupt:
                self.stop()
                break

    def _run_periodic_backend(self) -> None:
        """Run periodic full backend test."""
        print(f"\n[PERIODIC] Full backend test @ {datetime.now().strftime('%H:%M:%S')}")
        result = self.runner.run_backend_tests(quick=False)
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{status}] {result.test_count} tests, "
              f"{result.fail_count} failures ({result.duration:.2f}s)")

        if not result.passed:
            self.alert_manager.send_alert(result, "periodic_check")

        cov = self.coverage_reporter.parse_coverage_from_output(result.output)
        if cov is not None:
            self.coverage_reporter.record_coverage(cov)
            trend = self.coverage_reporter.get_trend()
            print(f"  Coverage: {cov:.1f}% (trend: {trend})")

    def _run_periodic_coverage(self) -> None:
        """Run coverage report generation."""
        print(f"\n[COVERAGE] Generating report @ {datetime.now().strftime('%H:%M:%S')}")
        result = self.runner.run_backend_coverage()
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{status}] {result.test_count} tests ({result.duration:.2f}s)")

        cov = self.coverage_reporter.parse_coverage_from_output(result.output)
        if cov is not None:
            self.coverage_reporter.record_coverage(cov)
            trend = self.coverage_reporter.get_trend()
            print(f"  Coverage: {cov:.1f}% (trend: {trend})")
            print(f"  Report:   {COVERAGE_DIR}/index.html")

    def _run_periodic_e2e(self) -> None:
        """Run E2E tests periodically."""
        print(f"\n[E2E] Running E2E tests @ {datetime.now().strftime('%H:%M:%S')}")
        result = self.runner.run_e2e_tests()
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{status}] {result.test_count} tests, "
              f"{result.fail_count} failures ({result.duration:.2f}s)")

        if not result.passed:
            self.alert_manager.send_alert(result, "periodic_e2e")

    def stop(self) -> None:
        """Stop the daemon."""
        self._running = False
        self.observer.stop()
        self.observer.join()
        print("\n[STOP] Continuous test daemon stopped.")


def run_full_suite() -> None:
    """Run full test suite (non-watch mode)."""
    runner = TestRunner()
    coverage_reporter = CoverageReporter(COVERAGE_DIR)

    print("=" * 60)
    print("  FULL TEST SUITE")
    print("=" * 60)

    print("\n[1/3] Backend tests...")
    be_result = runner.run_backend_tests(quick=False)
    status = "PASS" if be_result.passed else "FAIL"
    print(f"  [{status}] {be_result.test_count} tests, "
          f"{be_result.fail_count} failures ({be_result.duration:.2f}s)")

    print("\n[2/3] Frontend tests...")
    fe_result = runner.run_frontend_tests(quick=False)
    status = "PASS" if fe_result.passed else "FAIL"
    print(f"  [{status}] {fe_result.test_count} tests, "
          f"{fe_result.fail_count} failures ({fe_result.duration:.2f}s)")

    print("\n[3/3] Coverage...")
    cov_result = runner.run_backend_coverage()
    status = "PASS" if cov_result.passed else "FAIL"
    print(f"  [{status}] {cov_result.test_count} tests ({cov_result.duration:.2f}s)")

    cov = coverage_reporter.parse_coverage_from_output(cov_result.output)
    if cov is not None:
        coverage_reporter.record_coverage(cov)
        print(f"  Coverage: {cov:.1f}%")

    print("\n" + "=" * 60)
    all_passed = be_result.passed and fe_result.passed and cov_result.passed
    if all_passed:
        print("  ALL TESTS PASSED")
    else:
        print("  SOME TESTS FAILED")
    print("=" * 60)


def main() -> None:
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Continuous Test Daemon")
    parser.add_argument(
        "--full", action="store_true",
        help="Run full test suite once and exit",
    )
    parser.add_argument(
        "--backend-only", action="store_true",
        help="Only run backend tests in watch mode",
    )
    parser.add_argument(
        "--frontend-only", action="store_true",
        help="Only run frontend tests in watch mode",
    )
    parser.add_argument(
        "--no-periodic", action="store_true",
        help="Disable periodic full test runs",
    )
    parser.add_argument(
        "--e2e-interval", type=int, default=60,
        help="E2E test interval in cycles (default: 60)",
    )

    args = parser.parse_args()

    if args.full:
        run_full_suite()
    else:
        daemon = ContinuousTestDaemon()
        try:
            daemon.start()
        except KeyboardInterrupt:
            daemon.stop()


if __name__ == "__main__":
    main()
