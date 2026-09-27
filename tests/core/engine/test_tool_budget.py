"""On-demand tool loading tests.

45 registered tools cost roughly 2.6k tokens of schema on every request
(measured: 3,767 description chars plus 6,803 parameter chars). Anthropic's
tool-design research places 10-20 tools in the recommended range and reports
degradation in tool-selection accuracy past 30-50.

`build_tools` (app/core/engine/tools.py) already ranks tools against the task
description via ToolPrioritizer, but it returns every tool regardless of rank.
Ranking that does not change the payload only reorders noise.

These tests pin a real budget: a caller-supplied limit keeps the highest ranked
tools, always keeps an explicitly requested tool, and leaves the full set
untouched when no limit is configured.
"""

from __future__ import annotations

from typing import Any

from app.core.engine.tools import build_tools


class FakeDefinition:
    def __init__(self, name: str) -> None:
        self.name = name
        self.description = f"does {name}"
        self.parameters = {"type": "object", "properties": {}}


class FakeRegistry:
    def __init__(self, names: list[str]) -> None:
        self._defs = {name: FakeDefinition(name) for name in names}

    def get_tool(self, name: str):
        return self._defs.get(name)


class ReversePrioritizer:
    """Ranks the last input tool highest, so ordering is observable."""

    def rank_tools(self, task_description: str, tools: list[dict[str, Any]]) -> list[str]:
        names = [t["function"]["name"] for t in tools]
        return list(reversed(names))


NAMES = [f"tool_{i}" for i in range(10)]


def test_no_limit_keeps_every_tool() -> None:
    registry = FakeRegistry(NAMES)
    result = build_tools(registry, NAMES, ReversePrioritizer(), task_description="x")

    assert len(result) == len(NAMES)


def test_limit_keeps_the_highest_ranked_tools() -> None:
    registry = FakeRegistry(NAMES)
    result = build_tools(
        registry, NAMES, ReversePrioritizer(), task_description="x", max_tools=3
    )

    names = [t["function"]["name"] for t in result]
    assert len(names) == 3
    # ReversePrioritizer puts tool_9 first, so the survivors are the top ranks.
    assert names == ["tool_9", "tool_8", "tool_7"]


def test_limit_never_drops_an_explicitly_requested_tool() -> None:
    """A caller naming a tool means it, whatever the ranking says."""
    registry = FakeRegistry(NAMES)
    result = build_tools(
        registry,
        NAMES,
        ReversePrioritizer(),
        task_description="x",
        max_tools=2,
        always_include=["tool_0"],
    )

    names = [t["function"]["name"] for t in result]
    assert "tool_0" in names
    assert len(names) == 2


def test_limit_larger_than_the_tool_set_is_harmless() -> None:
    registry = FakeRegistry(NAMES)
    result = build_tools(
        registry, NAMES, ReversePrioritizer(), task_description="x", max_tools=100
    )

    assert len(result) == len(NAMES)


def test_always_include_can_exceed_the_limit() -> None:
    """Explicit requests outrank the budget; dropping them would be a bug."""
    registry = FakeRegistry(NAMES)
    result = build_tools(
        registry,
        NAMES,
        ReversePrioritizer(),
        task_description="x",
        max_tools=1,
        always_include=["tool_0", "tool_1"],
    )

    names = [t["function"]["name"] for t in result]
    assert set(names) == {"tool_0", "tool_1"}


def test_limit_applies_without_a_prioritizer() -> None:
    """Ranking is optional; the budget still has to hold."""
    registry = FakeRegistry(NAMES)
    result = build_tools(registry, NAMES, None, task_description="", max_tools=4)

    assert len(result) == 4


def test_registration_order_is_preserved_when_ranking_is_unavailable() -> None:
    """Without a prioritizer the caller keeps full control of the order."""
    registry = FakeRegistry(NAMES)
    result = build_tools(registry, NAMES, None, task_description="", max_tools=3)

    assert [t["function"]["name"] for t in result] == NAMES[:3]


def test_unregistered_names_are_never_returned() -> None:
    """The budget must not become a way to inject a nonexistent tool."""
    registry = FakeRegistry(NAMES)
    result = build_tools(
        registry,
        [*NAMES, "does_not_exist"],
        ReversePrioritizer(),
        task_description="x",
        max_tools=5,
    )

    names = [t["function"]["name"] for t in result]
    assert "does_not_exist" not in names
    assert len(names) == 5


def test_duplicate_candidates_are_sent_once_in_first_seen_order() -> None:
    registry = FakeRegistry(NAMES)
    result = build_tools(
        registry,
        ["tool_2", "tool_2", "tool_1", "tool_2"],
        None,
        max_tools=10,
    )

    assert [tool["function"]["name"] for tool in result] == ["tool_2", "tool_1"]


def test_duplicate_required_names_do_not_consume_budget_twice() -> None:
    registry = FakeRegistry(NAMES)
    result = build_tools(
        registry,
        NAMES,
        None,
        max_tools=2,
        always_include=["tool_0", "tool_0"],
    )

    assert [tool["function"]["name"] for tool in result] == ["tool_0", "tool_1"]


def test_engine_trims_a_session_that_asked_for_everything() -> None:
    """A session with no explicit tool list is the default set, so it is trimmed.

    `tools=[]` is the "give me the defaults" signal; a session that names tools
    has already made the choice itself.
    """
    from app.core.agent_engine import AgentEngine
    from app.core.session import AgentSession

    engine = AgentEngine.__new__(AgentEngine)
    session = AgentSession(session_id="s", agent_id="a", user_id="u", tools=[])

    assert engine._prompt_tool_budget(session) == 24


def test_engine_respects_an_explicit_tool_list() -> None:
    """Naming tools is a decision by the caller, so nothing gets dropped."""
    from app.core.agent_engine import AgentEngine
    from app.core.session import AgentSession

    engine = AgentEngine.__new__(AgentEngine)
    session = AgentSession(session_id="s", agent_id="a", user_id="u", tools=["read_file"])

    assert engine._prompt_tool_budget(session) is None


def test_env_override_controls_the_default_budget() -> None:
    import os

    from app.core.agent_engine import AgentEngine
    from app.core.session import AgentSession

    engine = AgentEngine.__new__(AgentEngine)
    session = AgentSession(session_id="s", agent_id="a", user_id="u", tools=[])

    os.environ["CLIMBER_MAX_PROMPT_TOOLS"] = "8"
    try:
        assert engine._prompt_tool_budget(session) == 8
        os.environ["CLIMBER_MAX_PROMPT_TOOLS"] = "0"
        assert engine._prompt_tool_budget(session) is None
        os.environ["CLIMBER_MAX_PROMPT_TOOLS"] = "junk"
        assert engine._prompt_tool_budget(session) == 24
    finally:
        os.environ.pop("CLIMBER_MAX_PROMPT_TOOLS", None)
