"""Empty tool registry wiring tests.

Three production sites constructed `ToolRegistry()` with no arguments, which
produces a registry with zero registered tools. Anything routed through them
silently had no tools available, and the resulting failure surfaced as a model
or "tool not found" error rather than a wiring bug:

- app/main.py built WorkflowEngine without tool_registry, and
  app/workflow/engine.py:361 fell back to `ToolRegistry()`.
- app/core/collaboration/base.py:690 passed a fresh ToolRegistry() to
  GroupCollaborationEngine.
- app/tools/builtins.py:580 built the decomposer AgentEngine the same way.

These tests pin that a registry obtained through the application path is the
populated one, and that the workflow engine refuses to guess.
"""

from __future__ import annotations

import pytest

from app.tools import ToolRegistry, get_tool_registry


def test_the_global_registry_is_populated() -> None:
    """Sanity check: the shared registry must actually hold the tools."""
    assert len(get_tool_registry()._tools) > 0


def test_di_resolves_the_populated_registry() -> None:
    """main.py registers the global registry under "ToolRegistry"."""
    from app.core.di import register, resolve

    registry = get_tool_registry()
    register("ToolRegistry", registry)
    assert resolve("ToolRegistry") is registry


def test_workflow_engine_never_builds_its_own_registry() -> None:
    """A missing registry must fail loudly, not degrade to an empty one."""
    from app.workflow.engine import WorkflowEngine

    class FakeEngine:
        pass

    engine = WorkflowEngine(engine=FakeEngine())  # type: ignore[arg-type]

    assert engine.tool_registry is None


@pytest.mark.asyncio
async def test_workflow_tool_node_refuses_an_unwired_engine() -> None:
    from app.workflow.engine import WorkflowEngine

    class FakeEngine:
        pass

    engine = WorkflowEngine(engine=FakeEngine())  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="tool_registry"):
        await engine._execute_tool_node(_make_tool_node(), {})


def _make_tool_node():
    from app.workflow import NodeType, WorkflowNode

    return WorkflowNode(
        id="n1",
        type=NodeType.TOOL,
        name="read",
        config={"tool_name": "read_file", "tool_inputs": {"path": "x"}},
    )


def test_collaboration_engine_receives_a_populated_registry() -> None:
    """The group collaboration engine must see real tools."""
    from app.core.collaboration.base import get_group_collaboration_engine
    from app.core.di import register

    registry = get_tool_registry()
    register("ToolRegistry", registry)
    engine = get_group_collaboration_engine()
    assert engine.tool_registry is registry
    assert len(engine.tool_registry._tools) > 0


def test_a_new_registry_is_empty_so_the_fallback_was_a_bug() -> None:
    """Document the failure mode the wiring bugs relied on."""
    assert len(ToolRegistry()._tools) == 0
