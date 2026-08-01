"""Hierarchical Sub-Agent Orchestrator — dynamic sub-agent dispatch.

Spawns isolated sub-agents for independent sub-tasks, with independent
memory sandboxes. Supports回收, destroy, and merge operations.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SubAgentState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SubAgentTask:
    id: str
    goal: str
    parent_id: str | None
    state: SubAgentState
    result: str = ""
    tokens_used: int = 0
    iterations: int = 0
    children: list[str] = field(default_factory=list)
    memory: dict[str, Any] = field(default_factory=dict)


@dataclass
class DispatchResult:
    task_id: str
    success: bool
    result: str
    tokens_used: int
    sub_results: list[dict[str, Any]] = field(default_factory=list)


class SubAgentOrchestrator:
    """Manage hierarchical sub-agent lifecycle."""

    def __init__(self, max_agents: int = 10, max_depth: int = 3):
        self._max_agents = max_agents
        self._max_depth = max_depth
        self._agents: dict[str, SubAgentTask] = {}
        self._active_count = 0

    def create_agent(
        self,
        goal: str,
        parent_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> SubAgentTask | None:
        """Create a new sub-agent if under limits."""
        if self._active_count >= self._max_agents:
            return None

        depth = self._get_depth(parent_id) + 1
        if depth > self._max_depth:
            return None

        task_id = str(uuid.uuid4())[:8]
        agent = SubAgentTask(
            id=task_id,
            goal=goal,
            parent_id=parent_id,
            state=SubAgentState.PENDING,
            memory=context or {},
        )
        self._agents[task_id] = agent
        self._active_count += 1

        if parent_id and parent_id in self._agents:
            self._agents[parent_id].children.append(task_id)

        return agent

    def dispatch(
        self,
        sub_tasks: list[dict[str, Any]],
        parent_id: str | None = None,
    ) -> list[DispatchResult]:
        """Dispatch multiple sub-tasks and collect results."""
        results = []
        agents: list[SubAgentTask] = []

        # Create agents
        for task in sub_tasks:
            agent = self.create_agent(
                goal=task["goal"],
                parent_id=parent_id,
                context=task.get("context"),
            )
            if agent:
                agents.append(agent)

        # Simulate execution (in real system, these would be async)
        for agent in agents:
            result = self._execute_agent(agent)
            results.append(result)

        return results

    def _execute_agent(self, agent: SubAgentTask) -> DispatchResult:
        """Execute a single sub-agent (simulated)."""
        agent.state = SubAgentState.RUNNING

        # In a real implementation, this would:
        # 1. Create an isolated context
        # 2. Run the agent loop
        # 3. Collect results
        # For now, simulate with metadata

        agent.state = SubAgentState.COMPLETED
        agent.result = f"Completed: {agent.goal[:50]}"
        agent.tokens_used = len(agent.goal) * 10  # simulated
        agent.iterations = 3  # simulated

        return DispatchResult(
            task_id=agent.id,
            success=True,
            result=agent.result,
            tokens_used=agent.tokens_used,
        )

    def cancel_agent(self, task_id: str) -> bool:
        """Cancel a running sub-agent."""
        agent = self._agents.get(task_id)
        if not agent or agent.state != SubAgentState.RUNNING:
            return False
        agent.state = SubAgentState.CANCELLED
        self._active_count -= 1
        return True

    def destroy_agent(self, task_id: str) -> bool:
        """Remove a completed/failed agent to free resources."""
        agent = self._agents.get(task_id)
        if not agent or agent.state == SubAgentState.RUNNING:
            return False
        del self._agents[task_id]
        return True

    def merge_results(self, task_ids: list[str]) -> dict[str, Any]:
        """Merge results from multiple sub-agents."""
        merged = {
            "goals": [],
            "total_tokens": 0,
            "total_iterations": 0,
            "success_count": 0,
            "fail_count": 0,
            "results": [],
        }

        for tid in task_ids:
            agent = self._agents.get(tid)
            if not agent:
                continue
            merged["goals"].append(agent.goal)
            merged["total_tokens"] += agent.tokens_used
            merged["total_iterations"] += agent.iterations
            if agent.state == SubAgentState.COMPLETED:
                merged["success_count"] += 1
            elif agent.state == SubAgentState.FAILED:
                merged["fail_count"] += 1
            merged["results"].append({
                "id": agent.id,
                "goal": agent.goal,
                "state": agent.state.value,
                "result": agent.result,
            })

        return merged

    def get_agent(self, task_id: str) -> SubAgentTask | None:
        return self._agents.get(task_id)

    def list_agents(
        self,
        state: SubAgentState | None = None,
    ) -> list[SubAgentTask]:
        agents = list(self._agents.values())
        if state:
            agents = [a for a in agents if a.state == state]
        return agents

    @property
    def active_count(self) -> int:
        return self._active_count

    @property
    def remaining_capacity(self) -> int:
        return self._max_agents - self._active_count

    def _get_depth(self, agent_id: str | None) -> int:
        depth = 0
        current = agent_id
        while current and current in self._agents:
            depth += 1
            current = self._agents[current].parent_id
        return depth

    def reset(self) -> None:
        self._agents.clear()
        self._active_count = 0
