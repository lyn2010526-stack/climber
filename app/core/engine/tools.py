"""Tool building and prioritization for the agent engine."""

from __future__ import annotations

from typing import Any

DEFAULT_MAX_TOOLS_IN_PROMPT = 24


def build_tools(
    tool_registry: Any,
    tool_names: list[str],
    tool_prioritizer: Any = None,
    task_description: str = "",
    max_tools: int | None = None,
    always_include: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Build tool definitions for the LLM, with optional prioritization.

    Args:
        tool_registry: The tool registry for looking up tool definitions.
        tool_names: List of tool names to include.
        tool_prioritizer: Optional prioritizer for ranking tools.
        task_description: Task description for context-aware ranking.
        max_tools: Maximum number of tool schemas to send. Ranking alone
            changes the order but not the payload size, and 45 tool schemas
            cost roughly 2.6k tokens per request. None or a non-positive value
            keeps every tool.
        always_include: Tool names that survive the budget regardless of rank.
            A caller that names a tool explicitly means it, so dropping one
            would silently change behaviour.

    Returns:
        A list of tool definition dictionaries.
    """
    names = _unique_names(tool_names)
    if task_description and len(names) > 1 and tool_prioritizer is not None:
        names = _rank_tools(tool_prioritizer, task_description, names, tool_registry)

    names = _apply_budget(names, tool_registry, max_tools, always_include)

    return [_make_tool_defn(tool_registry, name) for name in names if tool_registry.get_tool(name)]


def _apply_budget(
    names: list[str],
    tool_registry: Any,
    max_tools: int | None,
    always_include: list[str] | None,
) -> list[str]:
    """Trim the tool list to the budget, keeping required tools.

    Args:
        names: Candidate tool names, already in the order they should be sent.
        tool_registry: The tool registry, used to drop unregistered names.
        max_tools: Maximum tools to keep, or None/0 for no limit.
        always_include: Names that must survive the trim.

    Returns:
        The trimmed name list, in the incoming order.
    """
    registered = [name for name in _unique_names(names) if tool_registry.get_tool(name)]
    if not max_tools or max_tools <= 0:
        return registered

    required = [name for name in _unique_names(always_include or []) if name in registered]
    if len(required) >= max_tools:
        # Explicit requests outrank the budget: a caller naming five tools
        # with a limit of two still gets all five.
        return required

    budget = max_tools - len(required)
    required_set = set(required)
    optional = [name for name in registered if name not in required_set]
    return required + optional[:budget]


def _unique_names(names: list[str]) -> list[str]:
    """Keep the first occurrence of each tool name in caller order."""
    return list(dict.fromkeys(names))


def _rank_tools(
    tool_prioritizer: Any,
    task_description: str,
    tool_names: list[str],
    tool_registry: Any,
) -> list[str]:
    """Rank tools by relevance to the task description.

    Args:
        tool_prioritizer: The tool prioritizer instance.
        task_description: The task description for ranking.
        tool_names: Available tool names.
        tool_registry: The tool registry.

    Returns:
        A ranked list of tool names.
    """
    available: list[dict[str, Any]] = []
    unique_names = _unique_names(tool_names)
    for name in unique_names:
        defn = tool_registry.get_tool(name)
        if defn:
            available.append({
                "type": "function",
                "function": {
                    "name": defn.name,
                    "description": defn.description,
                    "parameters": defn.parameters,
                },
            })
    ranked = tool_prioritizer.rank_tools(task_description, available)
    name_to_defn = {name: tool_registry.get_tool(name) for name in unique_names}
    return [name for name in ranked if name in name_to_defn]


def _make_tool_defn(tool_registry: Any, name: str) -> dict[str, Any]:
    """Create a tool definition dictionary from the registry.

    Args:
        tool_registry: The tool registry.
        name: The tool name.

    Returns:
        A tool definition dictionary.
    """
    defn = tool_registry.get_tool(name)
    return {
        "type": "function",
        "function": {
            "name": defn.name,
            "description": defn.description,
            "parameters": defn.parameters,
        },
    }
