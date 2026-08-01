from __future__ import annotations

from typing import Any


def build_tools(
    tool_registry: Any,
    tool_prioritizer: Any,
    tool_names: list[str],
    task_description: str = "",
) -> list[dict[str, Any]]:
    if task_description and len(tool_names) > 1:
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
        tool_names = [name for name in ranked if name in name_to_defn]

    result = []
    for name in tool_names:
        defn = tool_registry.get_tool(name)
        if defn:
            result.append({
                "type": "function",
                "function": {
                    "name": defn.name,
                    "description": defn.description,
                    "parameters": defn.parameters,
                },
            })
    return result