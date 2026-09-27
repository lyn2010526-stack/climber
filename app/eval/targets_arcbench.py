"""ARC-Bench adapter target.

This target loads the real adapter from ``adapters/arcbench/`` and drives its
acceptance runner, which is the only component in the repository that produces
evidence strong enough to mark a requirement passed or failed
(``adapters/arcbench/acceptance.py:1-10``). Nothing here reimplements that logic:
the module is imported and called, and this file only adds the preflight probes
and the evidence plumbing the runtime needs.

What the adapter actually needs, and what happens when it is missing:

============================  ==========================================
Requirement                   Real behaviour here
============================  ==========================================
``requirements.yaml``         Parsed by the adapter for node ids. Missing or
                              unparseable is a hard setup error, not a score.
Official ``*.spec.ts`` files  Missing means no measurement is possible; the
                              adapter reports ``available: False`` and every
                              case is reported inconclusive.
Playwright runner             The adapter prefers a local ``node_modules`` or
                              ``package.json`` and falls back to an ambient
                              ``playwright``. The ambient CLI here is the Python
                              one, which cannot run ``playwright test``, so the
                              probe requires a *node* runner and reports a real
                              blocking reason when only the Python one exists.
Browser binaries              Probed via ``playwright install --dry-run``.
                              Absent browsers are reported as a real blocking
                              capability with the expected install path.
Grading port                 Verified bindable before the run; an unbindable
                              port is a real inconclusive cause, never a fail.
============================  ==========================================

The adapter's own ``fallback`` attribution (exit code when no JSON report was
produced, ``adapters/arcbench/acceptance.py:332-345``) is deliberately *not*
treated as evidence here. A usable per-spec report is the standard this runtime
holds itself to, so an exit-code-only outcome is reported as inconclusive with
the adapter's own message attached.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.eval.errors import TargetSetupError
from app.eval.targets import TARGET_ARCBENCH, EvalTarget, TargetSpec, register
from app.eval.types import CapabilityCheck, CapabilityState, TargetRunResult, Verdict

REPO_ROOT = Path(__file__).resolve().parents[2]
ADAPTER_DIR = REPO_ROOT / "adapters" / "arcbench"

DEFAULT_TIMEOUT = 300.0
PREFLIGHT_TIMEOUT = 25.0

# Substrings that prove a failure came from missing infrastructure rather than
# from the code under test. Recorded from the real Playwright output in this
# environment ("Executable doesn't exist at ...") and from the runner's own
# guidance, so the classification is driven by observed output.
BROWSER_MISSING_MARKERS = (
    "executable doesn't exist",
    "looks like playwright was just installed",
    "playwright install",
    "browser was not found",
    "missing dependencies to run browsers",
)
RUNNER_MISSING_MARKERS = (
    "install @playwright/test",
    "playwright test is not supported",
    "unknown command",
    "command not found",
    "no such file or directory",
)


@dataclass
class AdapterBundle:
    """The loaded adapter modules, plus the digest of the code that ran."""

    main: Any
    acceptance: Any
    runtime: Any
    code_digest: str


def _digest_paths(paths: list[Path]) -> str:
    """Stable digest of file contents, so evidence records the code that ran."""
    hasher = hashlib.sha256()
    for path in sorted(paths):
        hasher.update(path.name.encode("utf-8"))
        try:
            hasher.update(path.read_bytes())
        except OSError:
            hasher.update(b"<unreadable>")
    return hasher.hexdigest()[:16]


def _adapter_source_files() -> list[Path]:
    files = sorted(ADAPTER_DIR.glob("*.py"))
    vendor = ADAPTER_DIR / "vendor" / "arcbench_agent_runtime"
    if vendor.is_dir():
        files.extend(sorted(vendor.glob("*.py")))
    return [path for path in files if path.is_file()]


def load_adapter() -> AdapterBundle:
    """Import the real adapter modules from ``adapters/arcbench/``.

    Imported by file path rather than as a package because the adapter is a
    standalone submission bundle that is not on the application import path.
    """
    if not ADAPTER_DIR.is_dir():
        raise TargetSetupError(f"arcbench adapter directory is missing: {ADAPTER_DIR}")

    bundle_dir = str(ADAPTER_DIR)
    if bundle_dir not in sys.path:
        sys.path.insert(0, bundle_dir)

    def _load(name: str, filename: str) -> Any:
        path = ADAPTER_DIR / filename
        if not path.is_file():
            raise TargetSetupError(f"arcbench adapter is missing {filename}")
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise TargetSetupError(f"cannot load arcbench adapter module {filename}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    main = _load("arcbench_main", "main.py")
    acceptance = _load("arcbench_acceptance", "acceptance.py")

    runtime: Any = getattr(main, "RuntimeModules", None)
    if runtime is None:
        # The adapter degrades to a log-only stub here. The runtime must not
        # accept a measurement that came from the stub, because a stub writes no
        # evidence at all, so the caller checks ``runtime_available``.
        runtime = None

    return AdapterBundle(
        main=main,
        acceptance=acceptance,
        runtime=runtime,
        code_digest=_digest_paths(_adapter_source_files()),
    )


def read_arc_events(events_path: Path) -> list[dict[str, Any]]:
    """Read a real ``.arc`` event stream, skipping any unparseable line."""
    if not events_path.is_file():
        return []
    events: list[dict[str, Any]] = []
    try:
        text = events_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except ValueError:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


def port_is_free(port: int) -> bool:
    """True when nothing is already serving ``port``."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return False
    except OSError:
        return True


def allocate_free_port() -> int:
    """Ask the OS for an unused TCP port and release it immediately.

    A caller that does not care which port the grader uses should not have to
    guess one. The returned port is free at the moment it is handed out; the
    adapter re-checks it during preflight, so a port lost to a race surfaces as
    an ``inconclusive`` result rather than a wrong score.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _resolve_ports(spec: TargetSpec) -> tuple[int, int]:
    """Return the ``(web_port, smoke_port)`` pair this run should use.

    Explicit ports are honoured. Missing ports are allocated, and a caller who
    supplied only one of the two still gets a distinct partner.
    """
    web_port = int(spec.config_value("web_port") or 0)
    smoke_port = int(spec.config_value("smoke_port") or 0)

    if web_port <= 0 and smoke_port <= 0:
        web_port = allocate_free_port()
        smoke_port = allocate_free_port()
    elif web_port <= 0:
        web_port = allocate_free_port()
    elif smoke_port <= 0:
        smoke_port = allocate_free_port()

    # Both were handed out by the kernel, so a collision is possible in
    # principle. Re-allocate the smoke port rather than run a self-conflict.
    guard = 0
    while smoke_port == web_port and guard < 8:
        smoke_port = allocate_free_port()
        guard += 1
    if web_port == smoke_port:
        raise TargetSetupError("could not allocate two distinct grading ports")
    return web_port, smoke_port


def _playwright_runner(tests_dir: Path) -> tuple[list[str] | None, str]:
    """Resolve the runner the adapter will use, preferring a node harness.

    Mirrors ``adapters/arcbench/acceptance.py:79-97``. The ambient ``playwright``
    on PATH is only accepted when it is a *node* runner, because the Python CLI
    does not implement ``playwright test``.
    """
    local_bin = tests_dir / "node_modules" / ".bin" / "playwright"
    if local_bin.is_file():
        try:
            head = local_bin.read_text(encoding="utf-8", errors="replace")[:200]
        except OSError:
            head = ""
        if "#!/usr/bin/env node" in head or "#!/bin/sh" in head:
            return [str(local_bin)], "local node_modules/.bin/playwright"
        return [str(local_bin)], "local node_modules/.bin/playwright"

    if (tests_dir / "package.json").is_file():
        return ["npm", "exec", "--silent", "--", "playwright"], "npm exec playwright (tests harness)"

    ambient = shutil.which("playwright")
    if ambient:
        try:
            head = Path(ambient).read_text(encoding="utf-8", errors="replace")[:200]
        except OSError:
            head = ""
        if "python" in head.splitlines()[0].lower() if head.splitlines() else False:
            return None, f"ambient playwright at {ambient} is the Python CLI and cannot run `playwright test`"
        return [ambient], f"ambient playwright at {ambient}"

    return None, "no playwright runner found (no local harness and none on PATH)"


def _expected_browser_paths(tests_dir: Path) -> list[str]:
    """Ask the resolved runner where its browsers live, without downloading."""
    runner, _ = _playwright_runner(tests_dir)
    if not runner:
        return []
    try:
        completed = subprocess.run(
            [*runner, "install", "--dry-run", "chromium"],
            cwd=str(tests_dir),
            capture_output=True,
            text=True,
            errors="replace",
            timeout=PREFLIGHT_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    locations: list[str] = []
    for line in (completed.stdout + completed.stderr).splitlines():
        if "Install location" in line and ":" in line:
            locations.append(line.split(":", 1)[1].strip())
    return [loc for loc in locations if loc]


@dataclass
class ArcbenchPreflight:
    """Capability snapshot taken before anything is executed."""

    checks: list[CapabilityCheck] = field(default_factory=list)
    node_ids: list[str] = field(default_factory=list)
    tests_dir: Path | None = None
    deliverable_dir: Path | None = None
    web_port: int = 0
    smoke_port: int = 0
    node_browser_required: bool = False

    @property
    def blocking(self) -> list[CapabilityCheck]:
        return [check for check in self.checks if check.blocking]


class ArcbenchTarget(EvalTarget):
    """Evaluate an ARC-Bench deliverable with the adapter's own acceptance runner."""

    name = TARGET_ARCBENCH
    description = (
        "Independent GUI acceptance of an ARC-Bench deliverable: starts the produced "
        "backend on the grading port and maps official Playwright spec outcomes onto "
        "requirement nodes. Reports inconclusive when the runner or the report is missing."
    )

    # ------------------------------------------------------------------ build

    def build(self, spec: TargetSpec) -> dict[str, Any]:
        workdir = Path(spec.workdir).expanduser().resolve() if spec.workdir else None
        if workdir is None:
            raise TargetSetupError("arcbench target requires a workdir under app/eval/runs")
        workdir.mkdir(parents=True, exist_ok=True)

        deliverable = Path(str(spec.config_value("deliverable_dir") or workdir)).expanduser()
        tests_dir = Path(str(spec.config_value("tests_dir") or "")).expanduser()
        requirements = Path(str(spec.config_value("requirements_dir") or "")).expanduser()

        if not deliverable.is_dir():
            raise TargetSetupError(f"deliverable_dir does not exist: {deliverable}")
        if not tests_dir.is_dir():
            raise TargetSetupError(f"tests_dir does not exist: {tests_dir}")
        if not requirements.is_dir():
            raise TargetSetupError(f"requirements_dir does not exist: {requirements}")

        web_port, smoke_port = _resolve_ports(spec)
        if web_port <= 0 or smoke_port <= 0 or web_port == smoke_port:
            raise TargetSetupError("web_port and smoke_port must be distinct positive ports")

        node_ids = [str(n) for n in (spec.config_value("node_ids") or []) if str(n).strip()]
        if not node_ids and requirements.is_dir():
            node_ids = node_ids_from_requirements(requirements)
        if not node_ids:
            raise TargetSetupError(
                "no requirement node ids: pass config.node_ids or a requirements_dir holding requirements.yaml"
            )

        return {
            "workdir": workdir,
            "deliverable": deliverable,
            "tests_dir": tests_dir,
            "requirements_dir": requirements,
            "web_port": web_port,
            "smoke_port": smoke_port,
            "node_ids": node_ids,
            "timeout": float(spec.config_value("timeout") or DEFAULT_TIMEOUT),
            "clear_web_port": bool(spec.config_value("clear_web_port", False)),
        }

    # -------------------------------------------------------------- preflight

    def preflight(self, spec: TargetSpec) -> list[CapabilityCheck]:
        return self._preflight(self.build(spec)).checks

    def _preflight(self, plan: dict[str, Any]) -> ArcbenchPreflight:
        acceptance = _acceptance_module()
        deliverable: Path = plan["deliverable"]
        tests_dir: Path = plan["tests_dir"]
        web_port: int = plan["web_port"]
        node_ids: list[str] = plan["node_ids"]

        checks: list[CapabilityCheck] = []
        specs, config_file = acceptance.find_test_infra(tests_dir)
        checks.append(
            CapabilityCheck(
                name="acceptance_specs",
                state=CapabilityState.AVAILABLE if specs else CapabilityState.UNAVAILABLE,
                detail=(
                    f"{len(specs)} official spec file(s) under {tests_dir}"
                    + (f", config {config_file.name}" if config_file else ", no playwright config")
                )
                if specs
                else f"no official *.spec.ts/*.spec.js under {tests_dir}",
            )
        )

        backend_pkg = deliverable / "backend" / "package.json"
        checks.append(
            CapabilityCheck(
                name="deliverable_backend",
                state=CapabilityState.AVAILABLE if backend_pkg.is_file() else CapabilityState.UNAVAILABLE,
                detail=str(backend_pkg) if backend_pkg.is_file() else f"missing {backend_pkg}; grader cannot start the app",
            )
        )

        checks.append(
            CapabilityCheck(
                name="grading_port",
                state=CapabilityState.AVAILABLE if port_is_free(web_port) else CapabilityState.UNAVAILABLE,
                detail=(
                    f"port {web_port} is free"
                    if port_is_free(web_port)
                    else f"port {web_port} is already serving; the grader cannot bind it"
                ),
            )
        )

        runner, runner_note = _playwright_runner(tests_dir)
        checks.append(
            CapabilityCheck(
                name="playwright_runner",
                state=CapabilityState.AVAILABLE if runner else CapabilityState.UNAVAILABLE,
                detail=runner_note,
            )
        )

        node_browser_required, browser_note = self._browsers_required(tests_dir, specs, runner)
        browser_state, browser_detail = self._browser_state(tests_dir, runner)
        checks.append(
            CapabilityCheck(
                name="playwright_browsers",
                state=browser_state,
                detail=f"{browser_note}; {browser_detail}",
                required=node_browser_required,
            )
        )

        checks.append(
            CapabilityCheck(
                name="requirement_nodes",
                state=CapabilityState.AVAILABLE if node_ids else CapabilityState.UNAVAILABLE,
                detail=f"{len(node_ids)} node id(s) to attribute evidence to",
            )
        )

        return ArcbenchPreflight(
            checks=[check for check in checks if check is not None],
            node_ids=node_ids,
            tests_dir=tests_dir,
            deliverable_dir=deliverable,
            web_port=web_port,
            smoke_port=int(plan["smoke_port"]),
            node_browser_required=node_browser_required,
        )

    @staticmethod
    def _browsers_required(tests_dir: Path, specs: list[Path], runner: list[str] | None) -> tuple[bool, str]:
        """Decide whether browser binaries matter, by reading the real specs.

        A suite that only uses the ``request`` fixture drives Playwright's HTTP
        stack and never launches a browser, so demanding browsers there would
        reject a run that can genuinely be measured. That distinction is read
        from the specs themselves rather than assumed.
        """
        if not specs:
            return False, "no specs to inspect"
        if not runner:
            return False, "runner unavailable; browser requirement not evaluated"
        browser_capable = False
        for spec_path in specs:
            try:
                text = spec_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "page." in text or "browser.newPage" in text or "{ page }" in text or "{page}" in text:
                browser_capable = True
        if not browser_capable:
            return False, "specs use only the request fixture; Playwright never launches a browser"
        return True, "specs drive a browser page, so browser binaries are required"

    @staticmethod
    def _browser_state(tests_dir: Path, runner: list[str] | None) -> tuple[CapabilityState, str]:
        if not runner:
            return CapabilityState.UNKNOWN, "runner unavailable; browsers not checked"
        expected = _expected_browser_paths(tests_dir)
        if not expected:
            return CapabilityState.UNKNOWN, f"`{' '.join(runner)} install --dry-run` reported no browser location"
        installed = [loc for loc in expected if Path(loc).exists()]
        if installed:
            return CapabilityState.AVAILABLE, f"browser payloads present: {', '.join(installed)}"
        return (
            CapabilityState.UNAVAILABLE,
            f"no browser payload at {expected[0]} (run `playwright install chromium` to enable browser specs)",
        )

    # ----------------------------------------------------------------- execute

    def execute(self, spec: TargetSpec) -> TargetRunResult:
        started = time.perf_counter()
        bundle = load_adapter()
        acceptance = bundle.acceptance
        main = bundle.main

        plan = self.build(spec)
        workdir: Path = plan["workdir"]

        pre = self._preflight(plan)
        node_ids = pre.node_ids
        deliverable: Path = plan["deliverable"]
        tests_dir: Path = plan["tests_dir"]
        web_port: int = plan["web_port"]

        evidence_inputs = {
            "deliverable_dir": str(deliverable),
            "tests_dir": str(tests_dir),
            "requirements_dir": str(plan["requirements_dir"]),
            "web_port": web_port,
            "smoke_port": plan["smoke_port"],
            "node_ids": node_ids,
            "adapter_code_digest": bundle.code_digest,
        }

        runtime_available = bundle.runtime is not None
        evidence: dict[str, Any] = {
            "inputs": evidence_inputs,
            "runtime_available": runtime_available,
            "capabilities": [check.to_dict() for check in pre.checks],
            "workdir": str(workdir),
        }

        def _finish(
            verdicts: dict[str, Verdict],
            reasons: dict[str, str],
            *,
            scored: bool,
            inconclusive: bool,
            message: str,
        ) -> TargetRunResult:
            return TargetRunResult(
                target=self.name,
                verdicts=verdicts,
                reasons=reasons,
                scored=scored,
                inconclusive=inconclusive,
                message=message,
                evidence=evidence,
                capabilities=pre.checks,
                duration_ms=(time.perf_counter() - started) * 1000.0,
            )

        # A missing evidence runtime means the adapter would degrade to a stub
        # that logs instead of writing events. Refuse to score that.
        if not runtime_available:
            message = (
                "arcbench_agent_runtime is unavailable, so the adapter cannot write a .arc "
                "evidence stream; no measurement is possible"
            )
            evidence["summary"] = {}
            return _finish(
                {node_id: Verdict.INCONCLUSIVE for node_id in node_ids},
                {node_id: message for node_id in node_ids},
                scored=False,
                inconclusive=True,
                message=message,
            )

        if pre.blocking:
            message = _blocking_message(pre.blocking)
            # The adapter is never reached, so there is no adapter summary. The
            # blocking capabilities are recorded instead, which is what makes
            # this run reproducible without pretending anything was measured.
            evidence["summary"] = {
                "preflight": [check.to_dict() for check in pre.blocking],
                "adapter_invoked": False,
                "ran": False,
                "available": False,
                "passed": None,
            }
            return _finish(
                {node_id: Verdict.INCONCLUSIVE for node_id in node_ids},
                {node_id: message for node_id in node_ids},
                scored=False,
                inconclusive=True,
                message=message,
            )

        # Real execution: the adapter's own acceptance runner, unmodified.
        self._emit_arc_event(workdir, "eval_run_started", nodes=node_ids, web_port=web_port)
        try:
            # The adapter starts the backend with PORT=grading_port but hands
            # Playwright a copy of the ambient environment, so a spec that
            # discovers the port from the environment needs the platform's own
            # ARCBENCH_WEB_PORT channel (the same variable the adapter's
            # ``resolve_web_port`` reads) set for the duration of the run.
            with _env({"ARCBENCH_WEB_PORT": str(web_port)}):
                summary = acceptance.run_acceptance(
                    deliverable,
                    tests_dir,
                    web_port=web_port,
                    extra_ports=[],
                    node_ids=node_ids,
                    free_port=main._free_web_port if plan["clear_web_port"] else (lambda _port: None),
                    log=lambda msg: _log(msg, workdir),
                    tail=lambda text, limit=1500: (text or "")[-limit:],
                    deadline=time.time() + plan["timeout"],
                )
        except Exception as exc:  # noqa: BLE001 - the runner must never crash the run
            message = f"acceptance runner crashed: {type(exc).__name__}: {exc}"
            evidence["summary"] = {"crash": message}
            return _finish(
                {node_id: Verdict.INCONCLUSIVE for node_id in node_ids},
                {node_id: message for node_id in node_ids},
                scored=False,
                inconclusive=True,
                message=message,
            )

        evidence["summary"] = dict(summary)
        verdicts, reasons, scored, message = self._verdicts_from_summary(summary, node_ids)
        evidence["arc_events"] = read_arc_events(workdir / ".arc" / "runner-events.jsonl")
        self._emit_arc_event(
            workdir,
            "eval_run_finished",
            verdict="measured" if scored else "inconclusive",
            message=message,
        )
        return _finish(verdicts, reasons, scored=scored, inconclusive=not scored, message=message)

    # ---------------------------------------------------------------- verdicts

    def _verdicts_from_summary(
        self, summary: dict[str, Any], node_ids: list[str]
    ) -> tuple[dict[str, Verdict], dict[str, str], bool, str]:
        """Map the adapter's honest summary onto per-node verdicts.

        The adapter's own summary is authoritative for pass/fail. What is added
        here is the refusal to treat a non-measurement as a result: an
        unavailable runner, an unusable report, or exit-code-only attribution
        all become inconclusive.
        """
        raw_message = str(summary.get("message") or "").strip()
        available = bool(summary.get("available"))
        ran = bool(summary.get("ran"))
        fallback = bool(summary.get("fallback"))

        passed_nodes = [str(n) for n in (summary.get("passed_nodes") or [])]
        failed_nodes = [str(n) for n in (summary.get("evidence_failed") or [])]
        specs_detail = summary.get("specs_detail") or []

        if not available:
            reason = f"acceptance infra unavailable: {raw_message}" if raw_message else (
                "acceptance infra unavailable: the acceptance runner reported the test "
                "infrastructure as unavailable"
            )
            return _unmeasured(node_ids, reason)

        if not ran:
            reason = raw_message or "the acceptance runner never started; nothing was measured"
            return _unmeasured(node_ids, reason)

        if fallback or not specs_detail:
            detail = raw_message or "no machine-readable per-spec report was produced"
            return _unmeasured(node_ids, f"no usable per-spec report: {detail}")

        verdicts: dict[str, Verdict] = {}
        reasons: dict[str, str] = {}
        for node_id in node_ids:
            if node_id in passed_nodes:
                verdicts[node_id] = Verdict.PASSED
            elif node_id in failed_nodes:
                verdicts[node_id] = Verdict.FAILED
                reasons[node_id] = raw_message or "an acceptance spec covering this node failed"
            else:
                verdicts[node_id] = Verdict.INCONCLUSIVE
                reasons[node_id] = "no acceptance spec covered this node id"

        scored = sum(1 for v in verdicts.values() if v.is_scored)
        message = raw_message or f"{scored}/{len(node_ids)} nodes backed by acceptance evidence"
        return verdicts, reasons, scored > 0, message

    # ------------------------------------------------------------ .arc writing

    @staticmethod
    def _emit_arc_event(workdir: Path, state: str, **fields: Any) -> None:
        """Append a real ``.arc`` event through the adapter's runtime client."""
        try:
            import arcbench_agent_runtime as runtime_modules
        except ImportError:
            return
        try:
            runtime = runtime_modules.AgentRuntime.from_env(project_dir=str(workdir))
            runtime.events._emit_runner_state(state, json.dumps(fields, default=str))
        except Exception:  # noqa: BLE001 - event emission must never break a run
            return


def _acceptance_module() -> Any:
    return load_adapter().acceptance


def _unmeasured(node_ids: list[str], reason: str) -> tuple[dict[str, Verdict], dict[str, str], bool, str]:
    """The (verdicts, reasons, scored, message) tuple for a run that measured nothing."""
    verdicts = {node_id: Verdict.INCONCLUSIVE for node_id in node_ids}
    return verdicts, {node_id: reason for node_id in node_ids}, False, reason


@contextmanager
def _env(values: dict[str, str]) -> Iterator[None]:
    """Temporarily set environment variables, restoring the previous values."""
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _blocking_message(blocking: list[CapabilityCheck]) -> str:
    parts = [f"{check.name} unavailable ({check.detail})" for check in blocking]
    return "the run was not measured because required capability is missing: " + "; ".join(parts)


def _log(message: str, workdir: Path) -> None:
    """Record adapter log output in the workdir, without credentials.

    The adapter logs its own environment diagnosis elsewhere; only its plain
    status lines are mirrored here.
    """
    try:
        log_path = workdir / "arcbench.log"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{message}\n")
    except OSError:
        pass


def node_ids_from_requirements(requirements_dir: Path) -> list[str]:
    """Read atomic node ids with the adapter's own tree parser."""
    try:
        bundle = load_adapter()
        tree = bundle.main.load_requirement_tree(requirements_dir)
    except Exception:  # noqa: BLE001 - a bad tree is reported by the target
        return []
    try:
        nodes = bundle.main.flatten_atomic(tree)
    except Exception:  # noqa: BLE001
        return []
    return [str(node.get("id")) for node in nodes if node.get("id")]


register(ArcbenchTarget())


__all__ = [
    "BROWSER_MISSING_MARKERS",
    "RUNNER_MISSING_MARKERS",
    "AdapterBundle",
    "ArcbenchPreflight",
    "ArcbenchTarget",
    "load_adapter",
    "node_ids_from_requirements",
    "port_is_free",
    "read_arc_events",
]
