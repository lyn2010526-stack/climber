"""Hypothesis Simulator — multi-branch parallel path evaluation.

Generates multiple execution paths, estimates token cost and success
probability for each, selects the optimal route.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionPath:
    id: str
    description: str
    steps: list[dict[str, Any]]
    estimated_tokens: int
    estimated_success_rate: float  # 0.0-1.0
    risk_factors: list[str] = field(default_factory=list)
    score: float = 0.0


@dataclass
class SimulationResult:
    paths: list[ExecutionPath]
    selected_path: ExecutionPath | None
    reasoning: str


class HypothesisSimulator:
    """Generates and evaluates multiple execution strategies."""

    def __init__(self, token_budget: int = 8000):
        self._token_budget = token_budget
        self._complexity_costs = {
            "file_read": 200,
            "file_write": 300,
            "command": 400,
            "web_search": 500,
            "browser": 800,
            "code_generation": 600,
            "analysis": 300,
        }

    def simulate(
        self,
        goal: str,
        available_tools: list[str],
        context: dict[str, Any] | None = None,
    ) -> SimulationResult:
        """Generate multiple execution paths and pick the best."""
        paths = self._generate_paths(goal, available_tools, context or {})
        for path in paths:
            path.estimated_tokens = self._estimate_tokens(path)
            path.estimated_success_rate = self._estimate_success(path, available_tools)
            path.score = self._score_path(path)

        paths.sort(key=lambda p: p.score, reverse=True)
        selected = paths[0] if paths else None

        reasoning = self._build_reasoning(paths, selected)
        return SimulationResult(
            paths=paths,
            selected_path=selected,
            reasoning=reasoning,
        )

    def _generate_paths(
        self,
        goal: str,
        tools: list[str],
        context: dict[str, Any],
    ) -> list[ExecutionPath]:
        """Generate 2-4 distinct execution strategies."""
        paths = []
        tool_set = set(tools)

        # Path A: Direct execution (minimal steps)
        steps_a = self._plan_direct(goal, tool_set)
        if steps_a:
            paths.append(ExecutionPath(
                id="direct",
                description="Direct execution: minimal tool calls, straight to goal",
                steps=steps_a,
                estimated_tokens=0,
                estimated_success_rate=0.0,
            ))

        # Path B: Explore-first (understand then act)
        steps_b = self._plan_explore_first(goal, tool_set)
        if steps_b:
            paths.append(ExecutionPath(
                id="explore_first",
                description="Explore-first: gather context before taking action",
                steps=steps_b,
                estimated_tokens=0,
                estimated_success_rate=0.0,
            ))

        # Path C: Parallel decomposition (split into sub-tasks)
        steps_c = self._plan_parallel(goal, tool_set)
        if steps_c:
            paths.append(ExecutionPath(
                id="parallel",
                description="Parallel decomposition: split goal into independent sub-tasks",
                steps=steps_c,
                estimated_tokens=0,
                estimated_success_rate=0.0,
                risk_factors=["Requires sub-agent coordination"],
            ))

        # Path D: Iterative refinement (build incrementally)
        steps_d = self._plan_iterative(goal, tool_set)
        if steps_d:
            paths.append(ExecutionPath(
                id="iterative",
                description="Iterative refinement: build solution incrementally with verification",
                steps=steps_d,
                estimated_tokens=0,
                estimated_success_rate=0.0,
                risk_factors=["Higher token cost", "Slower execution"],
            ))

        return paths

    def _plan_direct(self, goal: str, tools: set[str]) -> list[dict[str, Any]]:
        steps = []
        if "run_command" in tools and any(kw in goal.lower() for kw in ["run", "execute", "build", "test"]):
            steps.append({"tool": "run_command", "purpose": "Execute target operation directly"})
        elif "write_file" in tools and any(kw in goal.lower() for kw in ["create", "write", "add", "implement"]):
            steps.append({"tool": "write_file", "purpose": "Write the required content"})
        elif "read_file" in tools and any(kw in goal.lower() for kw in ["read", "check", "find", "analyze"]):
            steps.append({"tool": "read_file", "purpose": "Read and analyze the target"})
        elif "web_search" in tools and any(kw in goal.lower() for kw in ["search", "find", "lookup"]):
            steps.append({"tool": "web_search", "purpose": "Search for required information"})
        else:
            steps.append({"tool": "run_command", "purpose": f"Address goal: {goal[:60]}"})
        return steps

    def _plan_explore_first(self, goal: str, tools: set[str]) -> list[dict[str, Any]]:
        steps = []
        if "list_files" in tools:
            steps.append({"tool": "list_files", "purpose": "Survey project structure"})
        if "read_file" in tools:
            steps.append({"tool": "read_file", "purpose": "Understand relevant files"})
        steps.extend(self._plan_direct(goal, tools))
        return steps

    def _plan_parallel(self, goal: str, tools: set[str]) -> list[dict[str, Any]]:
        return [
            {"tool": "analysis", "purpose": f"Decompose goal into sub-tasks: {goal[:60]}"},
            {"tool": "dispatch", "purpose": "Dispatch independent sub-tasks to parallel agents"},
            {"tool": "merge", "purpose": "Merge sub-task results into final output"},
        ]

    def _plan_iterative(self, goal: str, tools: set[str]) -> list[dict[str, Any]]:
        return [
            {"tool": "analysis", "purpose": "Create minimal viable solution"},
            {"tool": "read_file", "purpose": "Verify current state"},
            {"tool": "write_file", "purpose": "Apply incremental change"},
            {"tool": "run_command", "purpose": "Test the change"},
        ]

    def _estimate_tokens(self, path: ExecutionPath) -> int:
        total = 500  # base overhead
        for step in path.steps:
            tool = step.get("tool", "analysis")
            total += self._complexity_costs.get(tool, 300)
        return total

    def _estimate_success(self, path: ExecutionPath, available_tools: list[str]) -> float:
        rate = 0.7  # base
        # More steps = more failure points
        rate -= len(path.steps) * 0.05
        # Direct paths tend to succeed more
        if path.id == "direct":
            rate += 0.15
        # Explore-first is safer for complex tasks
        if path.id == "explore_first":
            rate += 0.1
        # Parallel has coordination overhead
        if path.id == "parallel":
            rate -= 0.1
        # Check tool availability
        for step in path.steps:
            if step.get("tool") in available_tools:
                rate += 0.02
        return min(0.95, max(0.2, rate))

    def _score_path(self, path: ExecutionPath) -> float:
        """Score = success_rate * (1 - token_ratio) - risk_penalty."""
        token_ratio = path.estimated_tokens / max(self._token_budget, 1)
        risk_penalty = len(path.risk_factors) * 0.05
        return path.estimated_success_rate * (1 - token_ratio * 0.5) - risk_penalty

    def _build_reasoning(
        self,
        paths: list[ExecutionPath],
        selected: ExecutionPath | None,
    ) -> str:
        if not selected:
            return "No viable execution path found."
        lines = [f"Selected '{selected.id}' (score: {selected.score:.2f})"]
        lines.append(f"  Success rate: {selected.estimated_success_rate:.0%}")
        lines.append(f"  Est. tokens: {selected.estimated_tokens}")
        if selected.risk_factors:
            lines.append(f"  Risks: {', '.join(selected.risk_factors)}")
        lines.append(f"\nEvaluated {len(paths)} total paths:")
        for p in paths:
            marker = " <-- selected" if p.id == selected.id else ""
            lines.append(f"  {p.id}: score={p.score:.2f}, success={p.estimated_success_rate:.0%}{marker}")
        return "\n".join(lines)
