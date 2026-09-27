"""Guard against dead duplicate tool-builders (research-100 tool-selection review).

Round 4/5 cross-validation and Round 16 found two dead duplicates
(app/core/engine/safety.py was already redirected; the duplicate
app/core/engine/tool_builder.build_tools had zero references). This guard keeps
the registry's build_tools wired to the single production implementation.
"""

from __future__ import annotations

import importlib

import pytest


def test_no_dead_tool_builder_module() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("app.core.engine.tool_builder")


def test_build_tools_resolves_to_production_module() -> None:
    from app.core.engine import build_tools as from_package
    from app.core.engine.tools import build_tools as from_module

    assert from_package is from_module


def test_engine_uses_production_build_tools() -> None:
    import app.core.agent_engine as engine_module
    from app.core.engine.tools import build_tools

    assert engine_module.build_tools is build_tools
