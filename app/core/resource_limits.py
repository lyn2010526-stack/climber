"""Centralized subprocess resource limits.

Single source of truth for the rlimit values applied to sandboxed child
processes. Previously duplicated independently in ``app/core/sandbox.py``
(``SandboxExecutor._restrict_resources``) and ``app/workflow/code_sandbox.py``
(module-level ``_MAX_*`` constants); both should converge onto these defaults.

``build_preexec`` produces a callback suitable for ``subprocess.Popen`` /
``asyncio.create_subprocess_exec`` ``preexec_fn``. Each limit is applied
independently: a single failing ``setrlimit`` (unsupported platform value,
invalid soft/hard pair, permission denial) logs a warning and continues so
one restrictive limit never blocks the others.
"""

from __future__ import annotations

import resource
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from collections.abc import Callable

logger = structlog.get_logger()

# Aligned with SandboxConfig.max_memory_mb = 256 and code_sandbox._MAX_MEMORY_BYTES.
DEFAULT_MAX_MEMORY_BYTES = 256 * 1024 * 1024
# Aligned with SandboxConfig.timeout_seconds = 30 (+5 grace); code_sandbox uses
# a shorter wall clock but the same soft/hard shape.
DEFAULT_CPU_SOFT_SECONDS = 30
DEFAULT_CPU_HARD_SECONDS = 35
# Aligned with sandbox.py (64); code_sandbox.py is stricter (32) but the shared
# default must stay workable for native shell pipelines.
DEFAULT_MAX_FILE_DESCRIPTORS = 64
# Only defined by sandbox.py today; adopted as the shared process cap.
DEFAULT_MAX_PROCESSES = 10

ResourceLimits = dict[str, tuple[int, int]]


def _default_limits() -> ResourceLimits:
    """Map resource attribute names to their (soft, hard) default pairs."""
    return {
        "RLIMIT_AS": (DEFAULT_MAX_MEMORY_BYTES, DEFAULT_MAX_MEMORY_BYTES),
        "RLIMIT_CPU": (DEFAULT_CPU_SOFT_SECONDS, DEFAULT_CPU_HARD_SECONDS),
        "RLIMIT_NOFILE": (DEFAULT_MAX_FILE_DESCRIPTORS, DEFAULT_MAX_FILE_DESCRIPTORS),
        "RLIMIT_NPROC": (DEFAULT_MAX_PROCESSES, DEFAULT_MAX_PROCESSES),
    }


def build_preexec(overrides: ResourceLimits | None = None) -> Callable[[], None]:
    """Build a ``preexec_fn`` callback applying the shared rlimits.

    ``overrides`` maps ``resource`` module attribute names (e.g.
    ``"RLIMIT_AS"``) to ``(soft, hard)`` tuples and is merged over the
    defaults. Unknown resource names are skipped with a warning.
    """
    limits = _default_limits()
    if overrides:
        limits.update(overrides)

    def _apply_limits() -> None:
        for name, (soft, hard) in limits.items():
            limit_id = getattr(resource, name, None)
            if limit_id is None:
                logger.warning("resource_limits.unsupported_resource", resource=name)
                continue
            try:
                resource.setrlimit(limit_id, (soft, hard))
            except (ValueError, OSError) as exc:
                logger.warning("resource_limits.setrlimit_failed", resource=name, error=str(exc))

    return _apply_limits
