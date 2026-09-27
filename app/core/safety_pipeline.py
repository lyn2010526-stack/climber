"""Safety Pipeline result types.

Provides the execution-result contract used by the layered safety sandbox
stack (L1 in-process sandbox, L2 Docker sandbox, L3 approval flow). The
Docker sandbox returns :class:`ExecutionResult`; consumers inspect
``returncode``, ``stdout``/``stderr`` and ``timed_out`` to route fallbacks.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExecutionResult:
    """Outcome of a sandboxed execution."""

    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    timed_out: bool = False
    error: str | None = None
