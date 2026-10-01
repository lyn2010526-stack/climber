"""Tests for the shared subprocess resource-limit module and native_run integration."""

from __future__ import annotations

import asyncio
import resource

from app.core.resource_limits import (
    DEFAULT_CPU_HARD_SECONDS,
    DEFAULT_CPU_SOFT_SECONDS,
    DEFAULT_MAX_FILE_DESCRIPTORS,
    DEFAULT_MAX_MEMORY_BYTES,
    DEFAULT_MAX_PROCESSES,
    build_preexec,
)
from app.tools.native_tools import native_run

_LIMIT_NAMES = ("RLIMIT_AS", "RLIMIT_CPU", "RLIMIT_NOFILE", "RLIMIT_NPROC")

# Generous ceilings so the callback can be applied to the current test process
# without disturbing pytest itself; every limit is restored in ``finally``.
_GENEROUS_MEMORY_BYTES = 2 * 1024 * 1024 * 1024
_GENEROUS_CPU_SECONDS = 3600
_GENEROUS_FILE_DESCRIPTORS = 512
_GENEROUS_PROCESSES = 1000


def _original_limits() -> dict[str, tuple[int, int]]:
    return {name: resource.getrlimit(getattr(resource, name)) for name in _LIMIT_NAMES}


def _generous_overrides() -> dict[str, tuple[int, int]]:
    # Keep each hard limit at its current value so restoring the original pair
    # never requires privileges; only the soft limits become generous ceilings.
    overrides: dict[str, tuple[int, int]] = {}
    for name, generous in (
        ("RLIMIT_AS", _GENEROUS_MEMORY_BYTES),
        ("RLIMIT_CPU", _GENEROUS_CPU_SECONDS),
        ("RLIMIT_NOFILE", _GENEROUS_FILE_DESCRIPTORS),
        ("RLIMIT_NPROC", _GENEROUS_PROCESSES),
    ):
        hard = resource.getrlimit(getattr(resource, name))[1]
        overrides[name] = (min(generous, hard), hard)
    return overrides


def _restore_limits(original: dict[str, tuple[int, int]]) -> None:
    for name in _LIMIT_NAMES:
        resource.setrlimit(getattr(resource, name), original[name])


def test_default_constants_exist_and_are_positive() -> None:
    assert DEFAULT_MAX_MEMORY_BYTES > 0
    assert DEFAULT_CPU_SOFT_SECONDS > 0
    assert DEFAULT_CPU_HARD_SECONDS > 0
    assert DEFAULT_MAX_FILE_DESCRIPTORS > 0
    assert DEFAULT_MAX_PROCESSES > 0
    assert DEFAULT_CPU_SOFT_SECONDS <= DEFAULT_CPU_HARD_SECONDS
    # Aligned with the historical 256 MB cap shared by sandbox.py and code_sandbox.py
    assert DEFAULT_MAX_MEMORY_BYTES == 256 * 1024 * 1024


def test_build_preexec_returns_callable_and_applies_limits() -> None:
    original = _original_limits()
    overrides = _generous_overrides()
    preexec = build_preexec(overrides)
    assert callable(preexec)
    try:
        preexec()
        for name, (soft, _hard) in overrides.items():
            applied = resource.getrlimit(getattr(resource, name))
            assert applied[0] == soft
            assert applied[1] == original[name][1]
    finally:
        _restore_limits(original)
    for name in _LIMIT_NAMES:
        assert resource.getrlimit(getattr(resource, name)) == original[name]


def test_build_preexec_is_exception_safe_per_limit() -> None:
    original = _original_limits()
    # soft > hard makes the RLIMIT_NOFILE setrlimit fail, but the callback must
    # absorb the failure and still apply the remaining (valid) limits.
    overrides = _generous_overrides()
    overrides["RLIMIT_NOFILE"] = (overrides["RLIMIT_NOFILE"][0] + 1024, 1)
    preexec = build_preexec(overrides)
    try:
        preexec()
        assert resource.getrlimit(resource.RLIMIT_NOFILE) == original["RLIMIT_NOFILE"]
        applied_as = resource.getrlimit(resource.RLIMIT_AS)
        assert applied_as[0] == overrides["RLIMIT_AS"][0]
    finally:
        _restore_limits(original)


def test_native_run_echo_still_works() -> None:
    result = asyncio.run(native_run(command="echo resource-limit-ok"))
    assert "resource-limit-ok" in result
