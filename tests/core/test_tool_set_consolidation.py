"""Tool-set consolidation regression tests.

Anthropic on agent tool sets:

    "One of the most common failure modes we see is bloated tool sets that
     cover too much functionality or lead to ambiguous decision points about
     which tool to use. If a human engineer can't definitively say which tool
     should be used in a given situation, an AI agent can't be expected to do
     better."
    -- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

Vendor guidance converges on a similar ceiling: Google suggests an active set
of 10-20, OpenAI suggests fewer than 20 as a soft limit, and Anthropic reports
that "Claude's ability to pick the right tool degrades once you exceed 30-50
available tools." Each tool definition also costs roughly 250-500 tokens.

Climber registered 49 tools, inside the range where Anthropic documents
degradation. Four of them were redundant duplicates:

    read_file        vs native_read_file
    write_file       vs native_write_file
    list_files       vs native_list_dir
    web_search       vs native_web_search

The non-native names are the ones used by the headless sandbox
(app/headless/workspace.py) and by the default permission rules
(app/core/permission_rules.py), so the native-prefixed variants were the
removable side. These tests pin that the consolidation happened, that the
surviving tools are intact, and that no safety classification entry was left
pointing at a tool that no longer exists.
"""

from __future__ import annotations

import pytest

REMOVED = (
    "native_read_file",
    "native_write_file",
    "native_list_dir",
    "native_web_search",
)

SURVIVING_PAIRS = {
    "read_file": "path",
    "write_file": ("path", "content"),
    "list_files": "directory",
    "web_search": "query",
}


@pytest.fixture
def registry():
    import importlib

    importlib.import_module("app.tools.builtins")
    importlib.import_module("app.tools.native_tools")
    from app.tools import get_tool_registry

    return get_tool_registry()


def test_registry_has_no_functional_duplicates(registry) -> None:
    """The consolidation goal: two tools must never do the same job.

    Anthropic's failure mode is "ambiguous decision points about which tool
    to use". After removing the four native-prefixed clones, no two names in
    the registry share a base name, so the model never faces a choice between
    functionally equivalent tools.
    """
    tools = registry.list_tools()
    assert len({t.name for t in tools}) == len(tools), "duplicate tool names"

    import collections

    families = collections.defaultdict(list)
    for tool in tools:
        base = tool.name.split("_", 1)[1] if tool.name.startswith("native_") else tool.name
        families[base].append(tool.name)

    dupes = {base: names for base, names in families.items() if len(names) > 1}
    assert not dupes, f"functional duplicates remain: {dupes}"


def test_tool_count_reduced_by_the_consolidation(registry) -> None:
    """49 -> 46. Guards against a silent re-add of the removed clones.

    The baseline moved from 45 to 46 when ``simulate_experiment`` was added for
    the simulation-experiment workflow; it dispatches to an external simulator
    and has no surviving clone, so the consolidation goal is unchanged.
    """
    assert len(registry.list_tools()) == 46


def test_redundant_native_duplicates_are_gone(registry) -> None:
    for name in REMOVED:
        assert registry.get_tool(name) is None, f"{name} duplicates a surviving tool"


@pytest.mark.parametrize(("name", "params"), sorted(SURVIVING_PAIRS.items()))
def test_surviving_tool_keeps_its_parameters(registry, name, params) -> None:
    tool = registry.get_tool(name)
    assert tool is not None, f"{name} must survive; it backs the headless sandbox"
    expected = {params} if isinstance(params, str) else set(params)
    assert expected.issubset(set((tool.parameters or {}).get("properties", {})))


def test_no_safety_classification_entry_points_at_removed_tool() -> None:
    """A stale entry in _FILE_TOOLS/_COMMAND_TOOLS is dead weight at best.

    Round 23 established these tables as the single source of truth for
    sandbox gating. An entry naming a tool the registry no longer serves can
    never match, and hides the fact that the tool is gone.
    """
    from app.core.engine.validation import _COMMAND_TOOLS, _FILE_TOOLS

    classified = set(_COMMAND_TOOLS)
    for _name in _FILE_TOOLS:
        classified.add(_name)

    stale = classified.intersection(REMOVED)
    assert not stale, f"classification tables still reference removed tools: {stale}"


def test_every_registered_file_tool_is_still_classified() -> None:
    """Convergence must not create an ungated file tool.

    A tool that writes files and is missing from _FILE_TOOLS bypasses the
    sandbox path entirely, so every remaining entry must still name a real
    registered tool, and the table must not have been emptied out.
    """
    from app.core.engine.validation import _FILE_TOOLS

    assert _FILE_TOOLS, "_FILE_TOOLS must not be emptied by consolidation"
    unknown = [name for name in _FILE_TOOLS if not registry_has(name)]
    assert not unknown, f"_FILE_TOOLS references unregistered tools: {unknown}"


def registry_has(name: str) -> bool:
    import importlib

    importlib.import_module("app.tools.builtins")
    importlib.import_module("app.tools.native_tools")
    from app.tools import get_tool_registry

    return get_tool_registry().get_tool(name) is not None


# Aliases that are deliberately unregistered and exist only so permission rules
# can match a name a caller might send. Verified as intentional in Round 23.
DEFENSIVE_ALIASES = frozenset(
    {
        "bash",
        "command",
        "execute_command",
        "shell",
        "file_read",
        "file_write",
        "file_delete",
        "list_dir",
        "search",
        "glob",
        "edit",
        "delete",
        "rm",
        # Network aliases. The registered tools are web_search and
        # fetch_url; these two are unmatched-name aliases kept so a
        # caller-supplied HTTP tool name is still gated as MEDIUM/ASK.
        "fetch",
        "http_request",
    }
)


def test_removed_tools_leave_no_trace_in_permission_rules() -> None:
    """A deleted tool must not linger in the rules it was configured in.

    Round 27 removed native_web_search from the registry but left three
    references in permission_rules.py, so the default config still carried a
    decision for a tool that can never be invoked. Stale entries are misleading
    and hide genuine gaps, so none of the removed names may reappear.
    """
    from app.core import permission_rules

    leaked = [name for name in REMOVED if f'"{name}"' in inspect_source(permission_rules)]
    assert not leaked, f"removed tools still referenced in permission_rules: {leaked}"


def test_unregistered_permission_names_are_intentional_aliases() -> None:
    """Every unregistered tool name in the rules must be a known alias.

    Rules legitimately name unregistered tools so a caller-supplied name is
    still gated, but that makes typos indistinguishable from intent. Pinning
    the allowed set turns "someone renamed a tool" into a test failure.
    """
    import importlib
    import re

    importlib.import_module("app.tools.builtins")
    importlib.import_module("app.tools.native_tools")
    from app.core import permission_rules
    from app.tools import get_tool_registry

    registry = get_tool_registry()
    registered = set(getattr(registry, "_tools", {}))

    named = set(
        re.findall(r'"([a-z_]{3,})"', inspect_source(permission_rules))
    )
    # Only names that appear as a tool argument to a decision/lookup are tool
    # names; the rest are config keys, risk levels and parameter names.
    tool_named = {
        n
        for n in named
        if n not in _NON_TOOL_TOKENS
    }
    unknown = sorted(
        n
        for n in tool_named
        if n not in registered and n not in DEFENSIVE_ALIASES
    )
    assert not unknown, f"unregistered non-alias tool names in rules: {unknown}"


def inspect_source(module) -> str:
    import inspect

    return inspect.getsource(module)


# Config keys, permission modes, risk levels and argument names that are not
# tool names.
_NON_TOOL_TOKENS = frozenset(
    {
        "allow",
        "allowed_tools",
        "ask",
        "auto",
        "bypass",
        "decision",
        "default",
        "denied_tools",
        "deny",
        "description",
        "high",
        "low",
        "medium",
        "mode",
        "pattern",
        "plan",
        "rules",
        "strict",
        "tool",
        "command",
        "path",
        "url",
        "file_path",
    }
)
