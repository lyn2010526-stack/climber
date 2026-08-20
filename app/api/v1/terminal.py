"""Terminal sandbox API.

Provides a safe, sandboxed command execution endpoint for the web terminal.
Every command runs inside SandboxExecutor with path-traversal protection,
blocked patterns, resource limits and a hard timeout. No shell is involved
(commands are split and executed directly), so injection is mitigated.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.core.sandbox import SandboxConfig, SandboxExecutor

router = APIRouter(dependencies=[Depends(get_current_user)])

_executor: SandboxExecutor | None = None


def _get_executor() -> SandboxExecutor:
    global _executor
    if _executor is None:
        _executor = SandboxExecutor(SandboxConfig())
    return _executor


class ExecRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=4096, description="Command to run")
    timeout: int | None = Field(None, ge=1, le=120, description="Timeout in seconds (default from sandbox config)")


class ExecResponse(BaseModel):
    output: str
    ok: bool


@router.post("/execute")
async def execute_command(req: ExecRequest) -> ExecResponse:
    """Execute a command inside the sandbox and return its output."""
    executor = _get_executor()
    output = await executor.execute(req.command, timeout=req.timeout)
    ok = not output.startswith("BLOCKED") and not output.startswith("TIMEOUT")
    return ExecResponse(output=output, ok=ok)


@router.get("/health")
async def terminal_health() -> dict[str, object]:
    return {"ok": True, "sandbox": "ready"}
