"""Deadlock (dependency-cycle) detection for multi-agent collaboration tasks."""

from __future__ import annotations

from typing import Any

WHITE, GRAY, BLACK = 0, 1, 2


def _normalize(dependencies: Any) -> dict[str, list[str]]:
    """Normalize edge-list or dict dependency inputs to {node: [deps]}.

    An edge ``(task, depends_on)`` and a dict entry
    ``{task: [depends_on, ...]}`` both express "task depends on
    depends_on".
    """
    normalized: dict[str, list[str]] = {}
    if isinstance(dependencies, dict):
        for node, dep_list in dependencies.items():
            if node is None:
                continue
            key = str(node)
            normalized.setdefault(key, [])
            for item in dep_list or ():
                if item is None:
                    continue
                dep = str(item)
                normalized[key].append(dep)
                normalized.setdefault(dep, [])
        return normalized
    for node, dep in dependencies or ():
        if node is None or dep is None:
            continue
        key, dep_key = str(node), str(dep)
        normalized.setdefault(key, []).append(dep_key)
        normalized.setdefault(dep_key, [])
    return normalized


def _canonical(cycle: list[str]) -> tuple[str, ...]:
    """Rotate a cycle so its smallest id comes first (for dedup)."""
    if not cycle:
        return ()
    start = min(range(len(cycle)), key=lambda i: cycle[i])
    return tuple(cycle[start:] + cycle[:start])


def detect_deadlock(dependencies: Any) -> list[list[str]]:
    """Detect dependency cycles (deadlocks) in a collaboration task graph.

    Accepts an edge list ``[(task, depends_on), ...]`` or a dict
    ``{task: [dependencies]}``. Returns a list of cycles, where each
    cycle is a list of node ids forming a closed wait loop. Returns an
    empty list when the graph is cycle-free.

    A cycle means every task in it waits on another task in the same
    loop, so none of them can ever be scheduled.
    """
    deps = _normalize(dependencies)
    color: dict[str, int] = {}
    stack: list[str] = []
    position: dict[str, int] = {}
    cycles: list[tuple[str, ...]] = []
    seen: set[tuple[str, ...]] = set()

    def visit(node: str) -> None:
        color[node] = GRAY
        stack.append(node)
        position[node] = len(stack) - 1
        for nxt in deps.get(node, ()):
            state = color.get(nxt, WHITE)
            if state == WHITE:
                visit(nxt)
            elif state == GRAY:
                cycle = tuple(stack[position[nxt] :] + [nxt])
                key = _canonical(list(cycle))
                if key not in seen:
                    seen.add(key)
                    cycles.append(cycle)
        stack.pop()
        position.pop(node, None)
        color[node] = BLACK

    for node in sorted(deps):
        if node not in color:
            visit(node)
    return [list(cycle) for cycle in cycles]


def deadlocked_task_ids(dependencies: Any) -> set[str]:
    """Return ids of all nodes that participate in at least one cycle."""
    involved: set[str] = set()
    for cycle in detect_deadlock(dependencies):
        involved.update(cycle)
    return involved


def topological_order(dependencies: Any) -> list[list[str]]:
    """Return tasks grouped into dependency levels (list of task-id lists).

    Level 0 contains tasks with no unmet dependencies; each following
    level contains tasks whose dependencies all appear in earlier
    levels. Tasks permanently blocked by a dependency cycle -- and tasks
    that transitively depend on them -- are omitted, so callers detect
    deadlocks separately with :func:`detect_deadlock`.
    """
    deps = _normalize(dependencies)
    nodes = {str(node) for node in dependencies if node is not None} if isinstance(dependencies, dict) else set(deps)
    indegree: dict[str, int] = dict.fromkeys(deps, 0)
    dependents: dict[str, list[str]] = {node: [] for node in deps}
    for node, dep_list in deps.items():
        if node not in nodes:
            continue
        for dep in dep_list:
            if dep not in nodes:
                continue
            dependents[dep].append(node)
            indegree[node] += 1
    levels: list[list[str]] = []
    frontier = sorted(node for node in nodes if indegree[node] == 0)
    while frontier:
        levels.append(list(frontier))
        next_frontier: list[str] = []
        for node in frontier:
            for dependent in dependents[node]:
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    next_frontier.append(dependent)
        frontier = sorted(next_frontier)
    return levels
