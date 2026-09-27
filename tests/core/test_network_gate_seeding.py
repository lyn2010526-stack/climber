"""Network gate seeding tests.

Round 31 seeded the egress gate from the environment inside
`ToolRegistry.__init__`, reading the class-level flag. That was wrong:
`__init__` runs for every `ToolRegistry()` construction, and several
production sites construct one with no arguments:

- app/workflow/engine.py:361   `self.tool_registry or ToolRegistry()`
- app/core/collaboration/base.py:690
- app/tools/builtins.py:580

The engine's sandbox sets the gate to False at startup, then the first
workflow tool node constructs a fresh registry and re-seeds the class flag
from the environment, silently restoring full network egress for the rest of
the process.

Seeding belongs at process start, not in a constructor. These tests pin that a
new registry never changes an explicit runtime decision, while the very first
registry still picks up the environment.
"""

from __future__ import annotations

from app.tools import ToolRegistry


def test_constructing_a_registry_does_not_reset_the_gate() -> None:
    """A fresh instance must not undo a decision made at runtime."""
    ToolRegistry.set_network_enabled(False)

    ToolRegistry()

    assert ToolRegistry.network_enabled() is False


def test_constructing_several_registries_leaves_the_gate_alone() -> None:
    ToolRegistry.set_network_enabled(True)
    ToolRegistry.set_network_enabled(False)

    for _ in range(3):
        ToolRegistry()

    assert ToolRegistry.network_enabled() is False


def test_explicit_decision_survives_a_registry_construction() -> None:
    """Opening the gate explicitly must also survive."""
    ToolRegistry.set_network_enabled(False)
    ToolRegistry.set_network_enabled(True)

    ToolRegistry()

    assert ToolRegistry.network_enabled() is True


def test_the_environment_seeds_the_gate_on_first_use() -> None:
    """Process start still honours the deployment setting."""
    import os

    os.environ["CLIMBER_ENABLE_NETWORK"] = "0"
    try:
        ToolRegistry.bootstrap_network_gate()
        assert ToolRegistry.network_enabled() is False
        os.environ["CLIMBER_ENABLE_NETWORK"] = "1"
        ToolRegistry.bootstrap_network_gate()
        assert ToolRegistry.network_enabled() is True
    finally:
        os.environ.pop("CLIMBER_ENABLE_NETWORK", None)
        ToolRegistry.bootstrap_network_gate()


def test_bootstrap_reports_the_environment_rather_than_guessing() -> None:
    """An absent CLIMBER_ENABLE_NETWORK keeps the historical default open.

    bootstrap is called exactly once at process start, so "unset" has to mean
    the documented default rather than fail closed: a local run with no
    environment file should still be able to use web_search.
    """
    import os

    os.environ.pop("CLIMBER_ENABLE_NETWORK", None)
    try:
        assert ToolRegistry.network_enabled_from_env() is True
    finally:
        ToolRegistry.bootstrap_network_gate()
