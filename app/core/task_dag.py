"""Task dependency DAG — topological ordering and cycle detection.

- AutoGen `HandoffMessage`
- CrewAI task dependency management
- LangGraph StateGraph edge conditions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskNode:
    task_id: str
    name: str
    dependencies: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class TaskDAG:
    """Directed acyclic graph for task dependency management.

    Supports:
    - Topological sorting
    - Cycle detection
    - Parallel execution groups
    """

    def __init__(self):
        self._nodes: dict[str, TaskNode] = {}

    def add_task(self, task: TaskNode) -> None:
        self._nodes[task.task_id] = task

    def get_task(self, task_id: str) -> TaskNode | None:
        return self._nodes.get(task_id)

    def topological_order(self) -> list[list[str]]:
        """Return tasks grouped by execution level (parallel-safe groups).

        Returns:
            List of lists, where each inner list contains tasks that can run in parallel.
        """
        in_degree: dict[str, int] = dict.fromkeys(self._nodes, 0)
        adjacency: dict[str, list[str]] = {tid: [] for tid in self._nodes}

        for task in self._nodes.values():
            for dep in task.dependencies:
                if dep in adjacency:
                    adjacency[dep].append(task.task_id)
                    in_degree[task.task_id] += 1

        result: list[list[str]] = []
        current_level = [tid for tid, deg in in_degree.items() if deg == 0]

        while current_level:
            result.append(current_level)
            next_level = []
            for tid in current_level:
                for neighbor in adjacency[tid]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_level.append(neighbor)
            current_level = next_level

        return result

    def detect_cycle(self) -> list[str] | None:
        """Detect cycles in the DAG. Returns cycle path or None."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = dict.fromkeys(self._nodes, WHITE)
        parent: dict[str, str | None] = dict.fromkeys(self._nodes)

        def dfs(node_id: str) -> list[str] | None:
            color[node_id] = GRAY
            task = self._nodes.get(node_id)
            if task:
                for dep in task.dependencies:
                    if dep not in color:
                        continue
                    if color[dep] == GRAY:
                        cycle = [dep, node_id]
                        current = node_id
                        while parent.get(current) and parent[current] != dep:
                            current = parent[current]
                            cycle.append(current)
                        cycle.reverse()
                        return cycle
                    if color[dep] == WHITE:
                        parent[dep] = node_id
                        result = dfs(dep)
                        if result:
                            return result
            color[node_id] = BLACK
            return None

        for tid in self._nodes:
            if color[tid] == WHITE:
                cycle = dfs(tid)
                if cycle:
                    return cycle
        return None

    def get_ready_tasks(self, completed: set[str]) -> list[str]:
        """Get tasks whose dependencies are all completed and that are not already completed."""
        ready = []
        for task in self._nodes.values():
            if task.task_id in completed:
                continue
            if all(dep in completed for dep in task.dependencies):
                ready.append(task.task_id)
        return ready

    def update_task_dependencies(self, task_id: str, new_deps: list[str]) -> bool:
        """Update the dependencies of a task.

        Returns True if successful, False if task not found or cycle detected.
        """
        if task_id not in self._nodes:
            return False

        # Save original deps for rollback
        original_deps = self._nodes[task_id].dependencies

        # Apply new deps
        self._nodes[task_id].dependencies = new_deps

        # Check for cycles
        if self.detect_cycle() is not None:
            # Rollback
            self._nodes[task_id].dependencies = original_deps
            return False

        return True


@dataclass
class HandoffMessage:
    """Agent handoff message — transfer context from one agent to another.

    """

    source_agent: str
    target_agent: str
    task_id: str
    context: str
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
