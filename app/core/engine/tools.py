"""Tool building and prioritization for the agent engine."""

from __future__ import annotations

from typing import Any


def build_tools(
    tool_registry: Any,
    tool_names: list[str],
    tool_prioritizer: Any = None,
    task_description: str = "",
) -> list[dict[str, Any]]:
    """Build tool definitions for the LLM, with optional prioritization.

    Args:
        tool_registry: The tool registry for looking up tool definitions.
        tool_names: List of tool names to include.
        tool_prioritizer: Optional prioritizer for ranking tools.
        task_description: Task description for context-aware ranking.

    Returns:
        A list of tool definition dictionaries.
    """
    names = tool_names
    if task_description and len(names) > 1 and tool_prioritizer is not None:
        names = _rank_tools(tool_prioritizer, task_description, names, tool_registry)

    return [_make_tool_defn(tool_registry, name) for name in names if tool_registry.get_tool(name)]


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
    for name in tool_names:
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
    name_to_defn = {name: tool_registry.get_tool(name) for name in tool_names}
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
