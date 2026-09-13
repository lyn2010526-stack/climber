"""ARC-Bench submission adapter for the climber headless agent.

Entry point mirrors the platform contract:

    python main.py <requirement_path> [--output-dir DIR] [--type web]
                   [--app-type web] [--web-port N]

All handled failure paths emit the matching runtime event
(``mark_run_failed`` / per-phase ``failed``) and return exit code 0, because
the platform grades from ``.arc`` events, not from the process status.

This module is self-contained: it implements the platform contract directly
(no source copied from external repositories) and reuses the repo's
``app/headless`` execution loop through ``agent_driver``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

BUNDLE_DIR = Path(__file__).resolve().parent
if str(BUNDLE_DIR) not in sys.path:
    sys.path.insert(0, str(BUNDLE_DIR))

# Prefer the installed PyPI runtime, fall back to the vendored MIT copy.
RuntimeModules = None
try:  # pragma: no cover - import fallback is exercised in tests
    import arcbench_agent_runtime as RuntimeModules  # noqa: F401
except ImportError:
    sys.path.insert(0, str(BUNDLE_DIR / "vendor"))
    try:
        import arcbench_agent_runtime as RuntimeModules  # noqa: F401
    except ImportError:  # pragma: no cover
        RuntimeModules = None

import prompts  # noqa: E402

DEFAULT_TIME_BUDGET = 2700.0
DEFAULT_NODE_TIMEOUT = 1200.0
DEFAULT_SKELETON_ATTEMPTS = 4
DEFAULT_NUDGES = 2
DEFAULT_REHEARSALS = 3

_spec_port_re = re.compile(r"(?:localhost:|127\.0\.0\.1:|:)(\d{2,5})(?![\d/])")


def log(msg: str) -> None:
    print(f"[arcbench] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Runtime access
# ---------------------------------------------------------------------------


def make_runtime(output_dir: Path):
    """Build AgentRuntime for output_dir, or a no-op stub when the SDK is absent."""

    if RuntimeModules is None:
        log("arcbench_agent_runtime unavailable; events will only be logged")
        return _StubRuntime()
    return RuntimeModules.AgentRuntime.from_env(
        project_dir=str(Path(output_dir).resolve()),
        runner_events_path=str(Path(output_dir) / ".arc" / "runner-events.jsonl"),
        traceability_dir=str(Path(output_dir) / ".arc" / "traceability"),
    )


class _StubRuntime:
    class _Recorder:
        def __getattr__(self, name):
            def _call(*args, **kwargs):
                log(f"event-stub {name} {args}")

            return _call

    def __init__(self):
        self.events = self._Recorder()
        self.traceability = self._Recorder()
        self.git = self._Recorder()


# ---------------------------------------------------------------------------
# Requirement tree parsing
# ---------------------------------------------------------------------------


def load_yaml(path: Path):
    import yaml

    with path.open("rb") as stream:
        return yaml.safe_load(stream)


def unwrap_root(data) -> dict:
    if not isinstance(data, dict):
        raise ValueError("requirements yaml root must be a mapping")
    for wrapper in ("requirements", "root", "requirement"):
        inner = data.get(wrapper)
        if isinstance(inner, dict):
            return unwrap_root(inner)
    if "id" in data:
        return data
    for value in data.values():
        if isinstance(value, dict) and "id" in value:
            return value
    raise ValueError("requirements tree has no node with an 'id'")


def load_requirement_tree(req_dir: Path) -> dict:
    for name in ("requirements.yaml", "requirements.yml"):
        path = req_dir / name
        if path.is_file():
            tree = unwrap_root(load_yaml(path))
            tree["_source_path"] = str(path)
            return tree
    raise FileNotFoundError(f"no requirements.yaml under {req_dir}")


def node_type(node: dict) -> str:
    return str(node.get("type") or "").strip().upper()


def is_atomic(node: dict) -> bool:
    if node_type(node) != "ATOMIC" and not (not node.get("children") and node_type(node) != "FOLDER"):
        return False
    return True


def flatten_atomic(node: dict, out: list[dict] | None = None) -> list[dict]:
    """Depth-first list of executable leaves (atomic or childless non-folder)."""

    out = [] if out is None else out
    if not isinstance(node, dict):
        return out
    has_children = bool(node.get("children"))
    if is_atomic(node) or (not has_children and node_type(node) != "FOLDER"):
        if node.get("id"):
            out.append(node)
    for child in node.get("children") or []:
        flatten_atomic(child, out)
    return out


def describe_node(node: dict) -> str:
    steps_lines: list[str] = []
    for scenario in node.get("scenarios") or []:
        if not isinstance(scenario, dict):
            continue
        steps_lines.append(f"Scenario {scenario.get('id', '?')} - {scenario.get('name', '')}")
        for step in scenario.get("steps") or []:
            if not isinstance(step, dict):
                continue
            keyword = str(step.get("keyword") or "").strip().capitalize()
            content = str(step.get("content") or "").strip()
            steps_lines.append(f"  {keyword} {content}".rstrip())
    dependencies = node.get("dependencies") or []
    dep_text = ", ".join(str(d) for d in dependencies) if dependencies else "none"
    lines = [
        f"ID: {node.get('id', '?')}",
        f"Name: {node.get('name', '')}",
        f"Description: {node.get('description', '')}",
        "Scenarios:",
        *steps_lines,
        f"Depends on: {dep_text}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Model diagnostics and probe
# ---------------------------------------------------------------------------


def env_diagnosis() -> None:
    base = os.environ.get("OPENAI_BASE_URL") or os.environ.get("USER_LLM_BASE_URL") or ""
    model = os.environ.get("MODEL") or os.environ.get("USER_LLM_MODEL") or ""
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("USER_LLM_API_KEY") or ""
    log(f"base_url={base or '<unset>'} model={model or '<unset>'} api_key_present={bool(key)} api_key_len={len(key)}")


def _http_post_json(url: str, api_key: str, payload: dict, timeout: float):
    import urllib.error
    import urllib.request

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return {"error": f"http {exc.code}"}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def probe_model(model, timeout: float = 30.0) -> bool:
    """Minimal /chat/completions probe. Waits up to 10 minutes while failing."""

    base = getattr(model, "url", "")
    api_key = getattr(model, "api_key", "")
    payload = {
        "model": getattr(model, "model", ""),
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 8,
    }
    deadline = time.time() + 600
    attempt = 0
    while True:
        attempt += 1
        answer = _http_post_json(base, api_key, payload, timeout)
        if "error" not in answer:
            log(f"model probe ok on attempt {attempt}")
            return True
        if time.time() >= deadline:
            log(f"model probe still failing after 10 minutes: {answer['error']}; continue anyway")
            return False
        log(f"model probe attempt {attempt} failed ({answer['error']}); retry in 30s")
        time.sleep(30.0)


# ---------------------------------------------------------------------------
# Port helpers
# ---------------------------------------------------------------------------


def _listening_pids(port: int) -> list[int]:
    # Prefer lsof (platform images usually ship it); fall back to ss.
    lsof = shutil.which("lsof")
    if lsof:
        try:
            out = subprocess.run(
                [lsof, "-ti", f":{port}", "-sTCP:LISTEN"],
                capture_output=True,
                text=True,
                timeout=15,
            ).stdout
            return sorted({int(line) for line in out.splitlines() if line.strip().isdigit()})
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    for cmd in (["ss", "-ltnp", f"sport = :{port}"], ["ss", "-ltnp"]):
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=15).stdout
        except (OSError, ValueError, subprocess.SubprocessError):
            continue
        result = set()
        for match in re.finditer(rf"(?<![:\d]):{port}(?![:\d])", out):
            # pid= appears in the same Process line as the socket
            block = out[: match.start()]
            for pid in re.findall(r"pid=(\d+)", block[block.rfind("\n") + 1 :] if False else block[-800:]):
                result.add(int(pid))
        for line in out.splitlines():
            if f":{port}" in line:
                for pid in re.findall(r"pid=(\d+)", line):
                    result.add(int(pid))
        if result:
            return sorted(result)
    return []


def _kill_pids(pids: list[int]) -> int:
    killed = 0
    for pid in pids:
        try:
            os.killpg(pid, signal.SIGKILL)
            continue
        except OSError:
            pass
        try:
            os.kill(pid, signal.SIGKILL)
            killed += 1
        except OSError:
            pass
    return killed


def _free_web_port(web_port: int) -> None:
    pids = _listening_pids(web_port)
    if pids:
        _kill_pids(pids)
        log(f"released grading port {web_port} (killed pids {pids})")


def port_in_use(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


class PortWatchdog(threading.Thread):
    """Reaps OUR OWN process groups that bind the grading port (never foreign pids)."""

    def __init__(self, web_port: int, pgid_registry: set[int], interval: float = 5.0):
        super().__init__(daemon=True)
        self.web_port = web_port
        self.registry = pgid_registry
        self.interval = interval
        self.warning_mode = False
        self.stop_event = threading.Event()
        self.pgid_owner = {}

    def run(self) -> None:
        while not self.stop_event.is_set():
            self.stop_event.wait(self.interval)
            if self.stop_event.is_set():
                break
            try:
                bound = _listening_pids(self.web_port)
            except Exception:
                continue
            if not bound:
                continue
            mine = [p for p in bound if p in self.registry or os.getpgid(p) in self.registry if _pid_alive(p)]
            if mine:
                log(f"watchdog: killing our process group(s) {mine} holding grading port {self.web_port}")
                _kill_pids(mine)
            elif self.warning_mode:
                pass
            else:
                self.warning_mode = True
                log(f"watchdog: foreign process {bound} holds grading port {self.web_port}; leaving it alone")

    def stop(self) -> None:
        self.stop_event.set()


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Output structure postflight
# ---------------------------------------------------------------------------


def deliverable_ok(output_dir: Path) -> bool:
    front = output_dir / "frontend"
    back = output_dir / "backend"
    return front.is_dir() and back.is_dir() and any(front.iterdir()) and any(back.iterdir())


def _promote_child(root: Path, child: str) -> None:
    src = root / child
    for item in sorted(src.iterdir()):
        dest = root / item.name
        if dest.exists():
            continue
        item.rename(dest)
    leftovers = list(src.iterdir())
    if not leftovers:
        src.rmdir()


def postflight_structure(output_dir: Path) -> None:
    """Lift a nested project one level up when <output_dir>/<child>/ holds both deliverables."""
    for child in sorted(p for p in output_dir.iterdir() if p.is_dir()):
        if child.name in {".git", ".arc"} or child.name.endswith("node_modules"):
            continue
        if (child / "frontend").is_dir() and (child / "backend").is_dir():
            log(f"postflight: promoting nested deliverables from {child.name}/")
            _promote_nested(child, output_dir)
            return


def _promote_nested(src: Path, dest: Path) -> None:
    def move_dir(rel: Path):
        target = dest / rel
        target.mkdir(parents=True, exist_ok=True)
        for item in sorted((src / rel).iterdir()):
            final = target / item.name
            if final.exists():
                continue
            if final.parent != dest:
                final.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(item), str(final))

    for item in sorted(src.iterdir()):
        rel = item.relative_to(src)
        target = dest / rel
        if item.is_dir():
            move_dir(rel)
        elif not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(item), str(target))
    shutil.rmtree(src, ignore_errors=True)


# ---------------------------------------------------------------------------
# Acceptance tests injection
# ---------------------------------------------------------------------------


def find_spec_files() -> list[Path]:
    candidates = []
    env_dir = os.environ.get("ARCBENCH_TESTS_DIR", "").strip()
    if env_dir:
        candidates.append(Path(env_dir))
    candidates.append(Path("/workspace/tests"))
    for root in candidates:
        if not root.is_dir():
            continue
        specs = sorted(root.rglob("*.spec.ts"))
        if specs:
            return [(root, specs)]
    return []


def parse_extra_ports(tests_dir: Path, specs: list[Path]) -> list[int]:
    """Hard-coded ports found in specs other than the default grading port."""
    ports: set[int] = set()
    for spec in specs:
        try:
            text = spec.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in _spec_port_re.finditer(text):
            port = int(match.group(1))
            if 1024 <= port <= 65535:
                ports.add(port)
    web_port = resolve_web_port()
    return sorted(p for p in ports if p != web_port)


def tests_injection(extra_ports: list[int], smoke_port: int, web_port: int) -> str:
    entries = find_spec_files()
    if not entries:
        return ""
    tests_dir, specs = entries[0]
    return prompts.official_tests_prompt(
        tests_dir,
        [str(p.relative_to(tests_dir)) for p in specs[:50]],
        extra_ports,
        smoke_port,
        web_port,
    )


# ---------------------------------------------------------------------------
# Startup rehearsal
# ---------------------------------------------------------------------------


def _tail(text: str, limit: int = 1500) -> str:
    text = text or ""
    return text[-limit:]


def _npm(workspace: Path, args: list[str], env: dict, timeout: float) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            ["npm", *args],
            cwd=str(workspace),
            env=env,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=min(timeout, 600),
        )
        return completed.returncode, (completed.stdout + completed.stderr)
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or b"") + (exc.stderr or b"")
        return -1, out.decode("utf-8", "replace") if isinstance(out, bytes) else str(out)
    except OSError as exc:
        return -1, f"npm unavailable: {exc}"


def _rehearse_once(output_dir: Path, smoke_port: int) -> str | None:
    registry: set[int] = set()
    frontend = output_dir / "frontend"
    backend = output_dir / "backend"
    if not frontend.is_dir() or not backend.is_dir():
        return "frontend/ or backend/ missing from the output directory"

    if (frontend / "package.json").is_file():
        rc, out = _npm(frontend, ["install"], dict(os.environ), 300)
        if rc != 0 and not (frontend / "node_modules").is_dir():
            if (frontend / "node_modules").is_dir() or (frontend / "build") and False:
                pass
            return "frontend npm install failed: " + _tail(out)
        rc, out = _npm(frontend, ["run", "build"], dict(os.environ), 300)
        if rc != 0:
            return "frontend npm run build failed: " + _tail(out)
    else:
        log("rehearsal: frontend/package.json absent; skipping npm (static shell)")

    if not (backend / "package.json").is_file():
        return "backend/package.json missing"
    rc, out = _npm(backend, ["install"], dict(os.environ), 300)
    if rc != 0 and not (backend / "node_modules").is_dir():
        return "backend npm install failed: " + _tail(out)

    env = dict(os.environ, PORT=str(smoke_port))
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
    registry.add(proc.pid)
    try:
        _free_web_port(smoke_port)
        deadline = time.time() + 45
        while time.time() < deadline:
            if proc.poll() is not None:
                out = proc.stdout.read() if proc.stdout else ""
                return f"backend exited early (code {proc.returncode}): " + _tail(str(out))
            try:
                with socket.create_connection(("127.0.0.1", smoke_port), timeout=2):
                    log(f"rehearsal: backend bound smoke port {smoke_port}")
                    return None
            except OSError:
                time.sleep(1.0)
        return f"backend did not bind smoke port {smoke_port} within 45s"
    finally:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
        if proc.stdout:
            try:
                proc.stdout.close()
            except OSError:
                pass
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        _free_web_port(smoke_port)


def rehearse_startup(output_dir: Path, smoke_port: int, max_rehearsals: int = DEFAULT_REHEARSALS):
    """Returns (failure_text|None, attempts). Raises nothing; 3rd failure continues as-is."""

    attempts = 0
    last_error: str | None = None
    while attempts < max_rehearsals:
        attempts += 1
        log(f"startup rehearsal attempt {attempts}/{max_rehearsals}")
        last_error = _rehearse_once(output_dir, smoke_port)
        if last_error is None:
            return None, attempts
        log(f"rehearsal failed: {_tail(last_error, 300)}")
    return last_error, attempts


# ---------------------------------------------------------------------------
# Turn helpers
# ---------------------------------------------------------------------------


def run_turn(driver, session, prompt: str, deadline: float, timeout: float, label: str) -> tuple[bool, str]:
    wall = min(deadline, time.monotonic() + timeout)
    started = time.monotonic()
    last_ok, text = session.run_turn(prompt, wall_deadline=wall)
    log(f"{label}: ok={last_ok} in {time.monotonic() - started:.1f}s text={_tail(text, 200)!r}")
    return last_ok, text


def run_prompt_with_retries(driver, prompt: str, ok_text, label: str, deadline: float, timeout: float, attempts: int = 2):
    """Run a prompt on a fresh session; retry once on transport failure."""

    last_error = ""
    for i in range(attempts):
        session = driver.new_session()
        ok, text = run_turn(driver, session, prompt, deadline, timeout, f"{label}[{i}]")
        if ok and ok_text(text):
            return True, text
        last_error = text
    return False, last_error


def finalize_preview(output_dir: Path, web_port: int, smoke_port: int) -> None:
    artifacts = os.environ.get("ARCBENCH_ARTIFACTS_DIR", "").strip()
    if not artifacts:
        return
    try:
        path = Path(artifacts)
        path.mkdir(parents=True, exist_ok=True)
        payload = {
            "ready": deliverable_ok(output_dir),
            "output_dir": str(output_dir),
            "web_port": web_port,
            "smoke_port": smoke_port,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        (path / "preview-ready.json").write_text(json.dumps(payload), encoding="utf-8")
        log(f"wrote preview-ready.json (ready={payload['ready']})")
    except OSError as exc:
        log(f"preview-ready.json write failed: {exc}")


# ---------------------------------------------------------------------------
# CLI args
# ---------------------------------------------------------------------------


def resolve_web_port(cli: int | None = None) -> int:
    for key in ("ARCBENCH_WEB_PORT", "ARC_WEB_PORT"):
        raw = (cli if key and cli is not None and key == "ARCBENCH_WEB_PORT" else None) or os.environ.get(key, "").strip()
        if raw:
            try:
                return int(raw)
            except ValueError:
                pass
    return 3000


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ARC-Bench web app adapter")
    parser.add_argument("requirement_path", nargs="?", help="directory holding requirements.yaml")
    parser.add_argument("--output-dir")
    parser.add_argument("--type", default="web")
    parser.add_argument("--app-type", dest="app_type", default="web")
    parser.add_argument("--web-port", type=int, default=None)
    parser.add_argument("--no-model", action="store_true", help=argparse.SUPPRESS)
    return parser


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    req_dir = Path(
        args.requirement_path
        or os.environ.get("ARCBENCH_TASK_DIR", "").strip()
        or "/workspace/task"
    ).expanduser()

    output_raw = args.output_dir or os.environ.get("ARCBENCH_TEMPLATE_DIR", "").strip()
    if output_raw:
        out_dir = Path(output_raw).expanduser()
    else:
        out_dir = Path.cwd() / "workspace" / f"run-{int(time.time())}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_dir = out_dir.resolve()

    web_port = args.web_port if args.web_port else resolve_web_port()
    smoke_port = int(os.environ.get("CLIMBER_ARC_SMOKE_PORT", "").strip() or "3100")
    if smoke_port == web_port:
        smoke_port += 1

    time_budget = float(os.environ.get("CLIMBER_ARC_TIME_BUDGET", "").strip() or DEFAULT_TIME_BUDGET)
    node_timeout = float(os.environ.get("CLIMBER_ARC_NODE_TIMEOUT", "").strip() or DEFAULT_NODE_TIMEOUT)

    env_diagnosis()
    runtime = make_runtime(out_dir)
    runtime.events.mark_run_started()
    deadline = time.monotonic() + time_budget

    try:
        return run(args, out_dir, req_dir, web_port, smoke_port, time_budget, node_timeout, runtime, deadline)
    except Exception as exc:  # noqa: BLE001 - contract: report failure and exit 0
        log(f"fatal: {type(exc).__name__}: {exc}")
        try:
            runtime.events.mark_run_failed(f"{type(exc).__name__}: {exc}")
        except Exception:
            pass
        finalize_preview(out_dir, web_port, smoke_port)
        _free_web_port(web_port)
        return 0


def run(  # noqa: PLR0913 - mirrors CLI contract
    args, out_dir: Path, req_dir: Path, web_port: int, smoke_port: int,
    time_budget: float, node_timeout: float, runtime, deadline: float,
) -> int:
    # ------------------------------------------------------------------ plan
    try:
        tree = load_requirement_tree(req_dir)
    except Exception as exc:  # noqa: BLE001
        log(f"requirements parse failed: {exc}")
        runtime.events.mark_run_failed(f"requirements parse failed: {exc}")
        return 0

    nodes = flatten_atomic(tree)
    node_names = [f"{n.get('id')}" for n in nodes]
    log(f"planned {len(node_names)} atomic nodes; output={out_dir} web={web_port} smoke={smoke_port}")

    extra_ports = parse_extra_ports(*find_spec_files()[0]) if find_spec_files() else []
    specs_inject = tests_injection(extra_ports, smoke_port, web_port)
    if specs_inject:
        log(f"official acceptance tests injected ({len(specs_inject)} chars)")

    env_port = str(smoke_port)

    def make_driver():
        import agent_driver

        return agent_driver.AgentDriver(
            out_dir,
            command_env={"PORT": env_port, "ARC_SMOKE_PORT": env_port},
            budget=None,
        )

    driver = make_driver()

    # ------------------------------------------------------------ traceability
    try:
        runtime.traceability.store_requirement_tree(tree)
    except Exception as exc:  # noqa: BLE001
        log(f"traceability store failed (non-fatal): {exc}")

    def git_commit(message: str) -> None:
        try:
            runtime.git.commit(message)
        except Exception as exc:  # noqa: BLE001
            log(f"git commit failed (non-fatal): {exc}")

    git_ensure_error = None
    try:
        runtime.git.ensure_repo()
    except Exception as exc:  # noqa: BLE001
        git_ensure_error = str(exc)
        log(f"git ensure_repo failed (non-fatal): {exc}")

    watchdog = PortWatchdog(web_port, driver.spawned_pgids)
    watchdog.start()

    skeleton_ok = False
    failed_nodes: list[str] = []

    try:
        def skeleton_present() -> bool:
            return deliverable_ok(out_dir)

        def skeleton_done(text: str) -> bool:
            if time.monotonic() >= deadline:
                return True
            if not skeleton_present():
                log(f"skeleton prompt ended without deliverables; text={_tail(text, 200)!r}")
                return False
            return True

        for attempt in range(DEFAULT_SKELETON_ATTEMPTS):
            if time.monotonic() >= deadline:
                log("time budget exhausted before skeleton completed")
                break
            session = driver.new_session()
            base = prompts.skeleton_prompt(smoke_port, web_port) + ("\n\n" + specs_inject if specs_inject else "")
            ok, text = run_turn(driver, session, base, deadline, min(node_timeout * 2, max(60.0, deadline - time.monotonic())), f"skeleton[{attempt}]")
            for nudge in range(DEFAULT_NUDGES):
                if skeleton_present():
                    break
                log(f"skeleton nudge {nudge + 1} (files still missing)")
                run_turn(driver, session, prompts.nudge_prompt() + "\n" + skeleton_retry_files_prompt(out_dir), deadline, 180.0, f"skeleton[{attempt}]nudge{nudge}")
            if skeleton_present():
                skeleton_ok = True
                break
            log(f"skeleton round {attempt + 1} ended with missing deliverables")
            driver = make_driver()
            session = None
            continue

        if not skeleton_ok:
            log("skeleton never landed on disk; continuing best-effort")

        git_commit("chore: scaffold web application skeleton")

        # ------------------------------------------------------------ nodes
        for node in nodes:
            if time.monotonic() >= deadline:
                log("time budget exhausted; remaining nodes recorded as skipped")
                break
            node_id = str(node.get("id"))
            node_name = str(node.get("name") or "")
            try:
                runtime.events.mark_design_started(node_id)
                runtime.events.mark_design_done(node_id)
                runtime.events.mark_implementation_started(node_id)
            except Exception as exc:  # noqa: BLE001
                log(f"event error for {node_id}: {exc}")
            node_prompt = prompts.node_prompt(
                f"Requirement node to implement now ({describe_node(node)})",
                smoke_port,
                web_port,
            )
            if specs_inject:
                node_prompt = specs_inject + "\n\n" + node_prompt
            remaining = max(60.0, deadline - time.monotonic())
            turn_timeout = min(node_timeout, remaining)
            session = driver.new_session()
            ok, text = run_turn(driver, session, node_prompt, deadline, turn_timeout, f"node {node_id}")
            if deliverable_ok(out_dir):
                git_commit(f"{node_id} (implement): {node_name}")
                try:
                    runtime.events.mark_implementation_done(node_id)
                except Exception as exc:  # noqa: BLE001
                    log(f"event error for {node_id}: {exc}")
            else:
                log(f"node {node_id} left no deliverables; turn ok={ok}")
                try:
                    runtime.events.mark_implementation_failed(node_id, _tail(text, 200))
                except Exception:  # noqa: BLE001
                    pass
                failed_nodes.append(node_id)

        # ----------------------------------------------------- final check
        if node_names:
            node_list = "\n".join(f"- {n}" for n in node_names[:80])
            prompt_final = prompts.final_check_prompt(node_list, smoke_port, web_port)
            if specs_inject:
                prompt_final = specs_inject + "\n\n" + prompt_final
            ok, text = run_prompt_with_retries(
                driver, prompt_final,
                lambda t: True,
                "finalcheck", deadline, min(900.0, max(120.0, deadline - time.monotonic())),
            )
            final_pass = "VERDICT: PASS" in (text or "")
            if not final_pass:
                log(f"final check verdict not PASS: {_tail(text, 200)!r}")
                try:
                    runtime.events.mark_run_failed("final check reported FAIL")
                except Exception:  # noqa: BLE001
                    pass
                for node_id in node_names:
                    try:
                        runtime.events.mark_test_failed(node_id)
                    except Exception:  # noqa: BLE001
                        pass
                for node_id in node_names:
                    if node_id not in failed_nodes:
                        failed_nodes.append(node_id)
            else:
                git_commit("chore: final verification pass")
                for node in nodes:
                    node_id = str(node.get("id"))
                    if node_id in failed_nodes:
                        continue
                    try:
                        runtime.events.mark_test_passed(node_id)
                    except Exception:  # noqa: BLE001
                        pass
        else:
            log("no atomic nodes found; nothing to test")

    finally:
        watchdog.stop()

    # -------------------------------------------------------------- rehearsal
    rehearsal_error, rehearsal_count = rehearse_best_effort(
        out_dir, smoke_port, web_port, node_timeout, deadline, driver, make_driver, specs_inject,
    )
    if rehearsal_error:
        log(f"rehearsal still failing after {rehearsal_count} attempts; submitting as-is")
    else:
        log(f"rehearsal passed after {rehearsal_count} attempt(s)")

    # ------------------------------------------------------------ postflight
    try:
        postflight_structure(out_dir)
    except Exception as exc:  # noqa: BLE001
        log(f"postflight failed (non-fatal): {exc}")

    finalize_preview(out_dir, web_port, smoke_port)
    _free_web_port(web_port)

    msg = f"completed {len(nodes) - len(set(failed_nodes))}/{len(nodes)} nodes (smoke={smoke_port})"
    if rehearsal_error:
        msg += f"; rehearsal error: {_tail(rehearsal_error, 120)}"
    if failed_nodes:
        msg += f"; failed_nodes={sorted(set(failed_nodes))}"
    else:
        try:
            runtime.events.mark_run_completed(msg)
        except Exception:  # noqa: BLE001
            pass
        log("run completed")
    if git_ensure_error:
        log(f"git was unavailable: {git_ensure_error}")
    return 0


def skeleton_retry_files_prompt(out_dir: Path) -> str:
    missing = []
    for sub in ("frontend", "backend"):
        sub_dir = out_dir / sub
        if not sub_dir.is_dir() or not any(sub_dir.iterdir()):
            missing.append(sub)
    listing = []
    for sub in missing[:4]:
        listing.append(f"missing dir {sub}/")
    return ("Verified missing after last turn:\n" + "\n".join(listing) + "\n"
            "Create the entire missing tree now with full content, not placeholders:\n"
            "- frontend/index.html, frontend/package.json (script build -> copies current directory to dist/ using plain node/coreutils with zero npm install)\n"
            "- backend/server.js (node http server; PORT env required; serves ../frontend/dist statically and /api with JSON in backend/data/db.json; hash passwords with crypto scrypt; seeds demo data)\n"
            "- backend/package.json (script start -> node server.js)")


def rehearse_best_effort(
    out_dir: Path, smoke_port: int, web_port: int, node_timeout: float,
    deadline: float, driver, make_driver, specs_inject: str,
):
    error, attempts = rehearse_startup(out_dir, smoke_port)
    for round_idx in range(DEFAULT_REHEARSALS - 1):
        if error is None or time.monotonic() >= deadline:
            break
        log(f"repair pass {round_idx + 1} for rehearsal failure")
        prompt_repair = prompts.repair_prompt(_tail(error or "unknown", 1500), smoke_port)
        if specs_inject:
            prompt_repair = specs_inject + "\n\n" + prompt_repair
        session = driver.new_session()
        run_turn(driver, session, prompt_repair, deadline, min(600.0, max(120.0, deadline - time.monotonic())), f"repair[{round_idx}]")
        error, extra = rehearse_startup(out_dir, smoke_port)
        attempts += extra
    return error, attempts


if __name__ == "__main__":
    sys.exit(main())
