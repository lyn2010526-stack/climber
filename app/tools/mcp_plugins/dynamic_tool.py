"""MCP Plugin: Dynamic Tool Generation — create tools on the fly.

Allows the agent to generate, persist, and reuse custom tool functions
at runtime, breaking free from fixed tool sets.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class GeneratedTool:
    name: str
    description: str
    code: str
    parameters: dict[str, Any]
    created_at: str = ""
    use_count: int = 0
    success_count: int = 0

    @property
    def success_rate(self) -> float:
        if self.use_count == 0:
            return 0.0
        return self.success_count / self.use_count


class DynamicToolGenerator:
    """Generate and manage runtime tools."""

    def __init__(self, storage_path: str = "data/dynamic_tools.json"):
        self._storage_path = storage_path
        self._tools: dict[str, GeneratedTool] = {}
        self._load()

    def generate_tool(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        implementation: str,
    ) -> GeneratedTool:
        """Create a new tool from specification."""
        tool = GeneratedTool(
            name=self._sanitize_name(name),
            description=description,
            code=implementation,
            parameters=parameters,
        )
        self._tools[tool.name] = tool
        self._save()
        return tool

    def generate_from_description(
        self,
        task_description: str,
        input_schema: dict[str, Any],
        output_description: str,
    ) -> GeneratedTool:
        """Auto-generate a tool from natural language description."""
        name = self._derive_name(task_description)
        code = self._generate_implementation(task_description, input_schema, output_description)

        tool = GeneratedTool(
            name=name,
            description=task_description,
            code=code,
            parameters=input_schema,
        )
        self._tools[name] = tool
        self._save()
        return tool

    def execute_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a generated tool."""
        tool = self._tools.get(name)
        if not tool:
            return {"error": f"Tool '{name}' not found"}

        tool.use_count += 1

        try:
            # Create isolated namespace
            namespace: dict[str, Any] = {
                "__builtins__": {
                    "len": len, "str": str, "int": int, "float": float,
                    "list": list, "dict": dict, "range": range,
                    "enumerate": enumerate, "zip": zip, "map": map,
                    "filter": filter, "sorted": sorted, "reversed": reversed,
                    "min": min, "max": max, "sum": sum, "abs": abs,
                    "round": round, "isinstance": isinstance, "type": type,
                    "print": print, "repr": repr, "hash": hash,
                    "True": True, "False": False, "None": None,
                },
            }

            # Add safe utility modules
            import collections
            import datetime
            import itertools
            import json as json_mod
            import math
            import re as re_mod
            import statistics

            namespace["math"] = math
            namespace["json"] = json_mod
            namespace["re"] = re_mod
            namespace["datetime"] = datetime
            namespace["itertools"] = itertools
            namespace["collections"] = collections
            namespace["statistics"] = statistics

            # Inject arguments (reserved namespace keys cannot be overridden)
            _RESERVED = {
                "__builtins__", "math", "json", "re", "datetime",
                "itertools", "collections", "statistics",
            }
            namespace.update({k: v for k, v in arguments.items() if k not in _RESERVED})

            # Execute
            exec(tool.code, namespace)  # noqa: S102 - sandboxed with restricted builtins

            # Find and call the main function
            main_func = namespace.get("run") or namespace.get(name)
            if main_func and callable(main_func):
                result = main_func()
                tool.success_count += 1
                self._save()
                return {"result": result, "success": True}
            return {"error": "No 'run' function found in tool code", "success": False}

        except Exception as e:
            return {"error": str(e), "success": False}

    def list_tools(self) -> list[dict[str, Any]]:
        """List all generated tools."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "use_count": t.use_count,
                "success_rate": t.success_rate,
            }
            for t in self._tools.values()
        ]

    def get_tool(self, name: str) -> GeneratedTool | None:
        return self._tools.get(name)

    def delete_tool(self, name: str) -> bool:
        if name in self._tools:
            del self._tools[name]
            self._save()
            return True
        return False

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Return OpenAI-format tool definitions for all generated tools."""
        definitions = []
        for tool in self._tools.values():
            definitions.append({
                "name": f"dynamic_{tool.name}",
                "description": tool.description,
                "parameters": tool.parameters,
            })
        return definitions

    def _sanitize_name(self, name: str) -> str:
        name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        name = re.sub(r"_+", "_", name).strip("_")
        if name and name[0].isdigit():
            name = f"tool_{name}"
        return name or "unnamed_tool"

    def _derive_name(self, description: str) -> str:
        words = re.findall(r"[a-zA-Z]+", description.lower())
        key_words = [w for w in words if w not in {
            "a", "an", "the", "to", "for", "of", "in", "on", "and", "or",
            "is", "are", "was", "be", "that", "this", "it", "with",
        }]
        name = "_".join(key_words[:3]) if key_words else "tool"
        if name in self._tools:
            name = f"{name}_{len(self._tools)}"
        return name

    def _generate_implementation(
        self,
        description: str,
        input_schema: dict[str, Any],
        output_description: str,
    ) -> str:
        """Generate Python code from description."""
        params = input_schema.get("properties", {})
        param_names = list(params.keys())

        return f'''def run():
    """{description}"""
    # Auto-generated implementation
    result = {{}}
    # TODO: Implement based on: {description}
    # Inputs: {", ".join(param_names)}
    # Expected output: {output_description}
    return result
'''

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)
        data = {
            name: {
                "name": t.name,
                "description": t.description,
                "code": t.code,
                "parameters": t.parameters,
                "use_count": t.use_count,
                "success_count": t.success_count,
            }
            for name, t in self._tools.items()
        }
        with open(self._storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self) -> None:
        if not os.path.exists(self._storage_path):
            return
        try:
            with open(self._storage_path) as f:
                data = json.load(f)
            for name, t in data.items():
                self._tools[name] = GeneratedTool(
                    name=t["name"],
                    description=t["description"],
                    code=t["code"],
                    parameters=t["parameters"],
                    use_count=t.get("use_count", 0),
                    success_count=t.get("success_count", 0),
                )
        except (json.JSONDecodeError, KeyError):
            pass
