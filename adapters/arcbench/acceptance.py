"""Independent GUI acceptance runner for ARC-Bench deliverables.

Starts the produced backend on the real grading port (exactly how the
official grader launches it), runs the official Playwright specs, and maps
per-spec outcomes onto atomic requirement nodes. Only this module provides
the evidence required for honest ``mark_test_passed`` / ``mark_test_failed``
events; whenever the test infra or a usable report is missing it reports
inconclusive instead of guessing.

Stdlib only; port helpers are injected by the caller to avoid import cycles
with main.py.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import tempfile
import time
from pathlib import Path

BOOT_TIMEOUT = 45.0
PLAYWRIGHT_TIMEOUT = 600.0

_CONFIG_NAMES = ("playwright.config.ts", "playwright.config.js", "playwright.config.mjs")
_FAILED_STATUSES = {"failed", "timedOut", "interrupted", "internalError"}


def find_test_infra(tests_dir: Path) -> tuple[list[Path], Path | None]:
    tests_dir = Path(tests_dir)
    specs = sorted(tests_dir.rglob("*.spec.ts")) if tests_dir.is_dir() else []
    if not specs and tests_dir.is_dir():
        specs = sorted(tests_dir.rglob("*.spec.js"))
    config = None
    for name in _CONFIG_NAMES:
        candidate = tests_dir / name
        if candidate.is_file():
            config = candidate
            break
    return specs, config


def wait_bound(port: int, proc, timeout: float) -> bool:
    """True when something serves the port before the timeout or process loss."""

    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                return True
        except OSError:
            time.sleep(1.0)
    return proc.poll() is None


def stop_server(proc) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except OSError:
        pass
    stdout = getattr(proc, "stdout", None)
    close = getattr(stdout, "close", None)
    if callable(close):
        try:
            close()
        except OSError:
            pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass


def playwright_argv(tests_dir: Path, config: Path | None) -> list[str]:
    """Prefer the harness shipped with the official tests directory.

    The grading environment provides its own Playwright setup. When specs
    live next to a package.json or a local playwright install, run through
    ``npm`` so versions match; only fall back to an ambient playwright when
    the directory carries no harness of its own.
    """

    argv = ["test", "--reporter=json"]
    if config is not None:
        argv += ["--config", str(config)]
    has_local_runner = (tests_dir / "node_modules").is_dir() or (tests_dir / "package.json").is_file()
    if has_local_runner:
        local_bin = tests_dir / "node_modules" / ".bin" / "playwright"
        if local_bin.is_file():
            return [str(local_bin), *argv]
        return ["npm", "exec", "--silent", "--", "playwright", *argv]
    return ["playwright", *argv]


def prepare_test_harness(tests_dir: Path, log, deadline: float) -> str | None:
    """npm install inside the official tests dir when it has deps but none installed."""

    if not (tests_dir / "package.json").is_file():
        return None
    if (tests_dir / "node_modules" / "@playwright").exists():
        return None
    timeout = max(60.0, min(300.0, deadline - time.time() - 60.0))
    try:
        completed = subprocess.run(
            ["npm", "install", "--no-audit", "--no-fund"],
            cwd=str(tests_dir),
            env=dict(os.environ, PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD="0"),
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return f"tests harness install failed: {exc}"
    if completed.returncode != 0:
        return "tests harness install failed: " + completed.stdout[-500:] + completed.stderr[-500:]
    return None


def parse_playwright_report(payload) -> list[dict] | None:
    """Flatten a Playwright JSON report into [{file, titles, passed}]."""

    if not isinstance(payload, dict):
        return None
    results: list[dict] = []

    def walk(suites, inherited_file, titles):
        for suite in suites or []:
            if not isinstance(suite, dict):
                continue
            file_name = suite.get("file") or inherited_file
            suite_title = suite.get("title")
            nested_titles = titles + (
                [suite_title]
                if isinstance(suite_title, str) and suite_title and suite_title != file_name
                else []
            )
            for spec in suite.get("specs") or []:
                if not isinstance(spec, dict):
                    continue
                if spec.get("ok") is not None:
                    passed = bool(spec.get("ok"))
                else:
                    statuses = [
                        str(res.get("status") or "")
                        for test in spec.get("tests") or []
                        if isinstance(test, dict)
                        for res in test.get("results") or []
                        if isinstance(res, dict)
                    ]
                    passed = bool(statuses) and all(
                        s and s not in _FAILED_STATUSES for s in statuses
                    )
                spec_titles = nested_titles + [t for t in [spec.get("title") or ""] if t]
                results.append({"file": file_name or "", "titles": spec_titles, "passed": passed})
            walk(suite.get("suites"), file_name, nested_titles)

    walk(payload.get("suites"), None, [])
    return results or None


def try_json_from_text(text: str):
    if not text or '"suites"' not in text:
        return None
    idx = text.find('"suites"')
    open_idx = text.rfind("{", 0, idx)
    while open_idx != -1:
        end = text.rfind("}", open_idx)
        while end > open_idx:
            try:
                return json.loads(text[open_idx : end + 1])
            except ValueError:
                end = text.rfind("}", open_idx, end)
        open_idx = text.rfind("{", 0, open_idx)
    return None


def map_results_to_nodes(results: list[dict], node_ids: list[str]) -> dict[str, bool]:
    """Attribute spec outcomes to requirement nodes by node-id mention."""

    assigned: dict[str, bool] = {}
    for res in results:
        haystack = " ".join([res.get("file", ""), *res.get("titles", [])])
        for node_id in node_ids:
            if node_id and node_id in haystack:
                current = assigned.get(node_id)
                value = bool(res.get("passed"))
                assigned[node_id] = value if current is None else (current and value)
    return assigned


def run_acceptance(
    output_dir: Path,
    tests_dir: Path,
    *,
    web_port: int,
    extra_ports,
    node_ids,
    free_port,
    log,
    tail,
    deadline: float,
) -> dict:
    """Evidence-quality summary; unknown nodes must never be marked passed."""

    node_ids = [str(n) for n in node_ids if n]
    summary = {
        "ran": False,
        "available": True,
        "passed": None,
        "all_specs_green": False,
        "passed_nodes": [],
        "evidence_failed": [],
        "unknown": list(node_ids),
        "fallback": False,
        "specs": 0,
        "specs_detail": [],
        "message": "",
    }
    tests_dir = Path(tests_dir)
    specs, config = find_test_infra(tests_dir)
    summary["specs"] = len(specs)
    if not specs:
        summary["available"] = False
        summary["message"] = f"no official spec files under {tests_dir}"
        return summary

    backend = Path(output_dir) / "backend"
    if not (backend / "package.json").is_file():
        summary.update(
            ran=True,
            passed=False,
            evidence_failed=node_ids,
            unknown=[],
            message=f"backend/package.json missing; grader could not start {web_port}",
        )
        return summary

    remaining_boot = max(10.0, min(BOOT_TIMEOUT, deadline - time.time()))
    env = dict(os.environ)
    env["PORT"] = str(web_port)
    env["ARC_EXTRA_PORTS"] = ",".join(str(p) for p in extra_ports) if extra_ports else "0"
    free_port(web_port)
    proc = subprocess.Popen(
        ["npm", "run", "start"],
        cwd=str(backend),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        start_new_session=True,
    )
    workdir: Path | None = None
    try:
        if not wait_bound(web_port, proc, remaining_boot):
            out = proc.stdout.read() if proc.stdout else ""
            summary.update(
                ran=True,
                passed=False,
                evidence_failed=node_ids,
                unknown=[],
                message=f"backend failed to bind grading port {web_port} on acceptance: "
                + tail(str(out), 600),
            )
            return summary
        log(f"acceptance: backend serving grading port {web_port}")

        budget = deadline - time.time() - 30.0
        if budget < 60:
            summary.update(
                ran=True,
                available=False,
                message=f"time budget exhausted before GUI acceptance ({int(budget)}s left)",
            )
            return summary

        harness_error = prepare_test_harness(tests_dir, log, deadline)
        if harness_error:
            summary.update(ran=True, available=False, message=harness_error)
            return summary

        workdir = Path(tempfile.mkdtemp(prefix="arc-accept-"))
        json_path = workdir / "report.json"
        run_env = dict(os.environ, PLAYWRIGHT_JSON_OUTPUT_NAME=str(json_path))
        argv = playwright_argv(tests_dir, config)
        log(f"acceptance: running {' '.join(argv)} (cwd={tests_dir})")
        try:
            completed = subprocess.run(
                argv,
                cwd=str(tests_dir),
                env=run_env,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=min(PLAYWRIGHT_TIMEOUT, max(60.0, budget)),
            )
            rc = completed.returncode
            combined = completed.stdout + completed.stderr
        except subprocess.TimeoutExpired as exc:
            rc = -1
            raw = exc.stdout or ""
            combined = (raw if isinstance(raw, str) else raw.decode("utf-8", "replace"))
            combined += "\nplaywright run exceeded its timeout"
        except OSError as exc:
            summary.update(ran=True, available=False, message=f"playwright unavailable: {exc}")
            return summary

        summary["ran"] = True
        report = None
        if json_path.is_file():
            try:
                report = json.loads(json_path.read_text(encoding="utf-8", errors="replace"))
            except ValueError as exc:
                log(f"acceptance: report.json unreadable ({exc}); trying stdout")
        if report is None:
            report = try_json_from_text(combined)
        parsed = parse_playwright_report(report)

        if parsed is None:
            if "no tests found" in combined.lower():
                summary.update(available=False, message="playwright found no runnable specs")
                return summary
            if "install @playwright/test" in combined:
                summary.update(available=False, message="playwright runner missing @playwright/test")
                return summary
            # No machine-readable per-spec outcome: fall back to the process
            # exit code, flagging the attribution as a fallback.
            passed = rc == 0
            summary["fallback"] = True
            summary["passed"] = passed
            if passed:
                summary["all_specs_green"] = True
                summary["passed_nodes"] = node_ids
            else:
                summary["evidence_failed"] = node_ids
            summary["unknown"] = []
            detail = "" if passed else tail(combined, 500)
            summary["message"] = "attributed by playwright exit code (no JSON report): " + detail
            return summary

        mapped = map_results_to_nodes(parsed, node_ids)
        passed_nodes = sorted(nid for nid, ok in mapped.items() if ok)
        evidence_failed = sorted(nid for nid, ok in mapped.items() if not ok)
        unknown = sorted(
            n for n in node_ids if n not in passed_nodes and n not in evidence_failed
        )
        failed_specs = sum(1 for r in parsed if not r["passed"])
        all_specs_green = failed_specs == 0 and rc == 0
        summary.update(
            all_specs_green=all_specs_green,
            passed=all_specs_green and not unknown,
            passed_nodes=passed_nodes,
            evidence_failed=evidence_failed,
            unknown=unknown,
            specs_detail=parsed,
            message=f"{len(parsed)} spec(s) executed, {failed_specs} failing"
            + (f"; unverified nodes: {unknown}" if unknown else ""),
        )
        return summary
    finally:
        if workdir is not None:
            for leftover in workdir.glob("*"):
                try:
                    leftover.unlink()
                except OSError:
                    pass
            try:
                workdir.rmdir()
            except OSError:
                pass
        stop_server(proc)


__all__ = [
    "find_test_infra",
    "wait_bound",
    "stop_server",
    "playwright_argv",
    "parse_playwright_report",
    "try_json_from_text",
    "map_results_to_nodes",
    "run_acceptance",
]
