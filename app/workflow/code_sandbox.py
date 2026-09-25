"""Subprocess-isolated execution for workflow code nodes.

The previous in-process ``exec()`` approach let a runaway loop, huge power
expression, or memory-hungry comprehension block the API worker. This module
runs each code node in a short-lived child interpreter with hard CPU, memory,
file-descriptor, file-size, wall-clock and output-size limits, plus a minimal
environment and a temp-dir-only working directory.

Protocol: the parent writes a JSON payload ``{"code": str, "inputs": dict}``
to the child's stdin. The child validates the AST, executes it against the
restricted builtin set, and prints ``{"ok": true, "result": ...}`` or
``{"ok": false, "error": "..."}`` as a single JSON line on stdout.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import sys
import tempfile
from typing import Any

_DEFAULT_TIMEOUT_SECONDS = 5
_MAX_TIMEOUT_SECONDS = 30
_MAX_MEMORY_BYTES = 256 * 1024 * 1024
_MAX_OUTPUT_BYTES = 64 * 1024
_MAX_INPUT_BYTES = 1 * 1024 * 1024


def _apply_child_limits() -> None:
    import resource

    resource.setrlimit(resource.RLIMIT_AS, (_MAX_MEMORY_BYTES, _MAX_MEMORY_BYTES))
    resource.setrlimit(resource.RLIMIT_CPU, (_DEFAULT_TIMEOUT_SECONDS + 2, _DEFAULT_TIMEOUT_SECONDS + 4))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))


def _child_main() -> None:
    raw = sys.stdin.buffer.read(_MAX_INPUT_BYTES + 1)
    if len(raw) > _MAX_INPUT_BYTES:
        json.dump({"ok": False, "error": "Code node input too large"}, sys.stdout)
        return

    from app.workflow.safe_code import safe_exec

    try:
        payload = json.loads(raw.decode("utf-8"))
        code = str(payload.get("code", ""))
        inputs = payload.get("inputs") or {}
        local_vars: dict[str, Any] = {"inputs": inputs, **inputs}
        safe_exec(code, local_vars)
        result = local_vars.get("result", {k: v for k, v in local_vars.items() if k != "inputs"})
        json.dump({"ok": True, "result": _jsonable(result)}, sys.stdout, default=str)
    except Exception as exc:
        json.dump({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, sys.stdout)


def _jsonable(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


async def run_code_sandboxed(
    code: str,
    inputs: dict[str, Any],
    timeout_seconds: int | float = _DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Execute workflow code in a resource-limited child process.

    Returns a dict with ``ok``, plus ``result`` on success or ``error`` on
    failure. Never raises for user-code problems; infrastructure failures
    surface as ``ok=False`` so the engine marks the node failed with a clear
    message.
    """
    effective_timeout = min(max(float(timeout_seconds), 1), _MAX_TIMEOUT_SECONDS)
    payload = json.dumps({"code": code, "inputs": inputs}, default=str)

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "PYTHONPATH": project_root,
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "HOME": tempfile.gettempdir(),
    }
    workdir = tempfile.mkdtemp(prefix="wf_code_")

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",
            "-c",
            "import sys; sys.path.insert(0, %r); "
            "from app.workflow.code_sandbox import _child_main; _child_main()" % project_root,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=workdir,
            env=env,
            preexec_fn=_apply_child_limits,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(payload.encode("utf-8")),
                timeout=effective_timeout + 2,
            )
        except TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            await proc.wait()
            return {"ok": False, "error": f"Code node exceeded {effective_timeout}s wall-clock limit"}
    except Exception as exc:
        return {"ok": False, "error": f"Code sandbox failed to start: {exc}"}
    finally:
        import shutil

        shutil.rmtree(workdir, ignore_errors=True)

    raw = stdout[:_MAX_OUTPUT_BYTES]
    if not raw:
        err_text = stderr.decode("utf-8", errors="replace").strip()[:500]
        reason = err_text or f"Code node terminated (exit={proc.returncode}, likely CPU/memory limit)"
        return {"ok": False, "error": reason}
    try:
        decoded = json.loads(raw.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"ok": False, "error": f"Code sandbox returned unreadable output: {raw[:200]!r}"}
    if not isinstance(decoded, dict):
        return {"ok": False, "error": "Code sandbox returned malformed output"}
    return decoded
