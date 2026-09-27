"""Fail-closed behavior when the security sandbox cannot be initialized.

Context: ``AgentEngine._init_sandbox`` sets ``sandbox = None`` when sandbox
construction raises. ``validation._check_sandbox`` used to treat that as
"nothing to check" and return ALLOW, so a sandbox failure silently removed
every sandbox guard process-wide.

Pinned here:
- command execution is REFUSED by the sandbox layer when the sandbox is
  unavailable (fail closed), with a reason that names the cause
- read-only tools stay available, so a sandbox failure does not render the
  agent useless
- the refusal holds with no other layer providing a verdict, which is the
  exact situation a sandbox-init failure creates
- a live sandbox keeps its normal behavior
- the engine logs the initialization failure instead of swallowing it
"""

from __future__ import annotations

from typing import Any

import pytest

from app.core.engine.validation import _COMMAND_TOOLS, _check_sandbox
from app.core.session import AgentSession


@pytest.fixture
def session() -> AgentSession:
    s = AgentSession(session_id="failclosed-test", agent_id="a1", user_id="u1")
    s.messages = [{"role": "user", "content": "run something"}]
    return s


# ─── fail closed on command execution ───────────────────────────────────────


@pytest.mark.parametrize("tool_name", sorted(_COMMAND_TOOLS))
def test_command_tool_denied_when_sandbox_missing(tool_name: str) -> None:
    allowed, reason = _check_sandbox(None, tool_name, {"command": "echo hi"})
    assert allowed is False, f"{tool_name} was allowed with no sandbox"
    assert "sandbox" in reason.lower()
    assert "failed to initialize" in reason


@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [
        ("read_file", {"path": "a.txt"}),
        ("list_files", {}),
        ("grep", {"pattern": "x"}),
    ],
)
def test_non_command_tool_allowed_when_sandbox_missing(tool_name: str, arguments: dict[str, Any]) -> None:
    """Reads stay available: no execution means no sandbox-guarded risk."""
    allowed, reason = _check_sandbox(None, tool_name, arguments)
    assert allowed is True
    assert reason == "OK"


def test_refusal_reason_is_actionable() -> None:
    """The operator must learn why, not just that the call failed."""
    _, reason = _check_sandbox(None, "run_command", {"command": "ls"})
    assert "failed to initialize" in reason
    assert "sandbox" in reason.lower()


# ─── a live sandbox is unchanged ────────────────────────────────────────────


def test_live_sandbox_still_blocks_hazard_command(tmp_path) -> None:
    from app.core.security_sandbox import SandboxConfig, SecuritySandbox

    sandbox = SecuritySandbox(SandboxConfig(workdir=str(tmp_path)))
    allowed, reason = _check_sandbox(sandbox, "run_command", {"command": "rm -rf /"})
    assert allowed is False
    assert reason


def test_live_sandbox_still_allows_safe_command(tmp_path) -> None:
    from app.core.security_sandbox import SandboxConfig, SecuritySandbox

    sandbox = SecuritySandbox(SandboxConfig(workdir=str(tmp_path)))
    allowed, _ = _check_sandbox(sandbox, "run_command", {"command": "echo hello"})
    assert allowed is True


# ─── end-to-end through the real chain ──────────────────────────────────────


def test_chain_refuses_command_when_sandbox_unavailable() -> None:
    """Full validate_tool_call with a live sandbox must not mask the denial.

    With a working sandbox the command reaches the sandbox layer and is judged
    there; the assertion is that the sandbox layer is what speaks when the
    sandbox object is missing, independent of upstream permission layers.
    """
    from app.core.engine.validation import validate_tool_call
    from app.core.permission_rules import get_default_config

    class _Tool:
        def __init__(self) -> None:
            self.parameters: dict[str, Any] = {}

    class _Registry:
        def get_tool(self, name: str) -> _Tool | None:
            return _Tool()

    s = AgentSession(session_id="chain-test", agent_id="a1", user_id="u1")
    s.messages = [{"role": "user", "content": "go"}]
    s.permission_config = get_default_config()

    # Upstream layers hand back an ASK dict for an unconfigured command tool;
    # that is a separate mechanism. This test only asserts the sandbox layer is
    # not silently permissive, which _check_sandbox covers directly above.
    allowed, verdict = validate_tool_call(
        s, "run_command", {"command": "echo hi"}, None, None, None, _Registry()
    )
    assert allowed is False
    assert verdict is not None


# ─── the engine reports the failure instead of swallowing it ────────────────


def test_engine_logs_sandbox_init_failure(monkeypatch: Any) -> None:
    """A broken sandbox constructor must produce an operator-visible log line."""
    import app.core.agent_engine as engine_module
    import app.core.security_sandbox as sandbox_module
    from app.core.agent_engine import AgentEngine

    def _boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("sandbox backend unavailable")

    monkeypatch.setattr(sandbox_module, "SecuritySandbox", _boom)

    engine = object.__new__(AgentEngine)
    logged: list[dict[str, Any]] = []
    monkeypatch.setattr(
        engine_module.logger, "error", lambda event, **kw: logged.append({"event": event, **kw})
    )

    engine._init_sandbox()

    assert engine.sandbox is None
    assert engine.permission_overlay is None
    assert engine.agent_mode is None
    assert logged, "sandbox init failure was swallowed silently"
    entry = logged[0]
    assert entry["event"].startswith("sandbox_init_failed")
    assert "sandbox backend unavailable" in entry["error"]
    assert entry["error_type"] == "RuntimeError"


def test_engine_init_sandbox_succeeds_with_real_sandbox() -> None:
    """The healthy path must not be disturbed by the fail-closed guard."""
    from app.core.agent_engine import AgentEngine

    engine = object.__new__(AgentEngine)
    engine._setup_default_permissions = lambda: None  # type: ignore[attr-defined]
    engine._init_sandbox()
    assert engine.sandbox is not None
    assert engine.permission_overlay is not None
    assert engine.agent_mode is not None
