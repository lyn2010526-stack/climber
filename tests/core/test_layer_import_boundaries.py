"""Tests for the app.core -> app.api layer dependency.

``app/api/v1/__init__.py`` aggregates every route module, including
``app.core.reasoning.api``. That module used to import ``app.api.v1.common``,
so importing it executed the aggregator while the aggregator was still running
and produced:

    AttributeError: partially initialized module
    'app.core.reasoning.api' has no attribute 'router'

The shared-engine accessor now lives in ``app/core/engine_registry.py`` and the
principal lookup is inlined, so ``app.core`` no longer reaches into ``app.api``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


def _import_in_fresh_interpreter(module: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.mark.parametrize(
    "module",
    [
        "app.core.reasoning.api",
        "app.core.engine_registry",
        "app.api.v1",
        "app.core.recovery",
        "app.api.v1.common",
    ],
)
def test_module_imports_standalone(module):
    """Each module must import on its own, not only as part of app.main."""
    result = _import_in_fresh_interpreter(module)
    assert result.returncode == 0, f"{module} failed to import:\n{result.stderr}"


def test_core_layer_does_not_import_the_api_package():
    """app.core.reasoning.api must not reach into app.api.v1."""
    result = _import_in_fresh_interpreter("app.core.reasoning.api")
    assert result.returncode == 0

    source = Path("app/core/reasoning/api.py").read_text(encoding="utf-8")
    assert "from app.api.v1" not in source, "core layer must not import the API layer"


def test_engine_accessor_is_shared():
    """chat and v1 must delegate to the core accessor, not hold their own.

    Building an engine needs a populated DI container, so this asserts the
    delegation wiring rather than instantiating one.
    """
    import app.api.v1 as v1
    import app.api.v1.chat as chat
    import app.core.engine_registry as registry

    assert chat.get_engine is not registry.get_engine
    assert v1.get_engine is not registry.get_engine

    sentinel = object()
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(registry, "get_engine", lambda: sentinel)
        assert chat.get_engine() is sentinel
        assert v1.get_engine() is sentinel
    finally:
        monkeypatch.undo()


def test_reasoning_resolves_the_caller_without_the_api_helper():
    """The local current_user_id must read the same principal as the API one."""
    from app.api.v1.common import current_user_id as api_current_user_id
    from app.core.reasoning.api import current_user_id as core_current_user_id

    class _Request:
        pass

    # Both read the ambient principal, so an un-set context yields the same
    # local default rather than diverging.
    assert core_current_user_id(_Request()) == api_current_user_id(_Request())
