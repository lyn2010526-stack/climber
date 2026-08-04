"""Capability Discovery — combine existing tools to create new capabilities.

When existing tools are insufficient, automatically compose multiple
basic tools into a new temporary reusable capability.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ComposedCapability:
    name: str
    description: str
    tool_chain: list[dict[str, Any]]
    inputs: dict[str, Any]
    output_description: str
    use_count: int = 0
    success_count: int = 0

    @property
    def success_rate(self) -> float:
        if self.use_count == 0:
            return 0.0
        return self.success_count / self.use_count


class CapabilityDiscovery:
    """Discover and compose new capabilities from existing tools."""

    def __init__(self, storage_path: str = "data/discovered_capabilities.json"):
        self._storage_path = storage_path
        self._capabilities: dict[str, ComposedCapability] = {}
        self._load()

    def discover(
        self,
        goal: str,
        available_tools: list[str],
        missing_capability: str,
    ) -> ComposedCapability | None:
        """Find a composition of existing tools that fulfills the missing capability."""
        composition = self._try_compose(goal, available_tools, missing_capability)
        if composition:
            self._capabilities[composition.name] = composition
            self._save()
        return composition

    def _try_compose(
        self,
        goal: str,
        tools: list[str],
        missing: str,
    ) -> ComposedCapability | None:
        """Try to compose a solution from available tools."""
        tool_set = set(tools)
        missing_lower = missing.lower()

        # Pattern: need to read + process + write
        if any(kw in missing_lower for kw in ["analyze", "parse", "extract", "transform"]):
            if "read_file" in tool_set and "write_file" in tool_set:
                return ComposedCapability(
                    name=self._make_name(missing),
                    description=f"Composed capability: {missing}",
                    tool_chain=[
                        {"tool": "read_file", "purpose": "Read input data"},
                        {"tool": "run_command", "purpose": "Process/transform data"},
                        {"tool": "write_file", "purpose": "Write processed output"},
                    ],
                    inputs={"input_path": {"type": "string"}, "output_path": {"type": "string"}},
                    output_description="Processed data written to output path",
                )

        # Pattern: need to search + collect
        if any(kw in missing_lower for kw in ["search", "find", "collect", "gather"]):
            if "web_search" in tool_set or "read_file" in tool_set:
                chain = []
                if "web_search" in tool_set:
                    chain.append({"tool": "web_search", "purpose": "Search for information"})
                if "read_file" in tool_set:
                    chain.append({"tool": "read_file", "purpose": "Read local references"})
                if "write_file" in tool_set:
                    chain.append({"tool": "write_file", "purpose": "Save collected data"})
                if chain:
                    return ComposedCapability(
                        name=self._make_name(missing),
                        description=f"Composed capability: {missing}",
                        tool_chain=chain,
                        inputs={"query": {"type": "string"}},
                        output_description="Collected and saved information",
                    )

        # Pattern: need to monitor/watch
        if any(kw in missing_lower for kw in ["monitor", "watch", "track", "observe"]):
            if "read_file" in tool_set and "run_command" in tool_set:
                return ComposedCapability(
                    name=self._make_name(missing),
                    description=f"Composed capability: {missing}",
                    tool_chain=[
                        {"tool": "read_file", "purpose": "Read current state"},
                        {"tool": "run_command", "purpose": "Compare with previous state"},
                        {"tool": "write_file", "purpose": "Log changes"},
                    ],
                    inputs={"target_path": {"type": "string"}, "interval": {"type": "number"}},
                    output_description="Change log of monitored target",
                )

        # Pattern: need to validate/verify
        if any(kw in missing_lower for kw in ["validate", "verify", "check", "test"]):
            if "read_file" in tool_set and "run_command" in tool_set:
                return ComposedCapability(
                    name=self._make_name(missing),
                    description=f"Composed capability: {missing}",
                    tool_chain=[
                        {"tool": "read_file", "purpose": "Read target to validate"},
                        {"tool": "run_command", "purpose": "Run validation logic"},
                    ],
                    inputs={"target": {"type": "string"}},
                    output_description="Validation result (pass/fail with details)",
                )

        # Pattern: database access
        if any(kw in missing_lower for kw in ["database", "db", "query", "sql"]):
            if "run_command" in tool_set:
                return ComposedCapability(
                    name=self._make_name(missing),
                    description=f"Composed capability: {missing} (via CLI)",
                    tool_chain=[
                        {"tool": "run_command", "purpose": "Execute database CLI command"},
                        {"tool": "read_file", "purpose": "Read query results"},
                    ],
                    inputs={"query": {"type": "string"}},
                    output_description="Database query results",
                )

        return None

    def list_capabilities(self) -> list[dict[str, Any]]:
        return [
            {
                "name": c.name,
                "description": c.description,
                "tools": [s["tool"] for s in c.tool_chain],
                "success_rate": c.success_rate,
            }
            for c in self._capabilities.values()
        ]

    def get_capability(self, name: str) -> ComposedCapability | None:
        return self._capabilities.get(name)

    def record_usage(self, name: str, success: bool) -> None:
        cap = self._capabilities.get(name)
        if cap:
            cap.use_count += 1
            if success:
                cap.success_count += 1
            self._save()

    def _make_name(self, description: str) -> str:
        words = re.findall(r"[a-zA-Z]+", description.lower())
        key_words = [w for w in words if w not in {
            "a", "an", "the", "to", "for", "of", "in", "on", "and", "or", "is",
        }]
        name = "_".join(key_words[:3]) if key_words else "capability"
        if name in self._capabilities:
            name = f"{name}_{len(self._capabilities)}"
        return name

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)
        data = {
            name: {
                "name": c.name,
                "description": c.description,
                "tool_chain": c.tool_chain,
                "inputs": c.inputs,
                "output_description": c.output_description,
                "use_count": c.use_count,
                "success_count": c.success_count,
            }
            for name, c in self._capabilities.items()
        }
        with open(self._storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self) -> None:
        if not os.path.exists(self._storage_path):
            return
        try:
            with open(self._storage_path) as f:
                data = json.load(f)
            for name, c in data.items():
                self._capabilities[name] = ComposedCapability(
                    name=c["name"],
                    description=c["description"],
                    tool_chain=c["tool_chain"],
                    inputs=c["inputs"],
                    output_description=c["output_description"],
                    use_count=c.get("use_count", 0),
                    success_count=c.get("success_count", 0),
                )
        except (json.JSONDecodeError, KeyError):
            pass
