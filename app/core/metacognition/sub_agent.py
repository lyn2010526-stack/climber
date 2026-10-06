"""Hierarchical Sub-Agent Orchestrator — dynamic sub-agent dispatch.

Spawns isolated sub-agents for independent sub-tasks, with independent
memory sandboxes. Supports回收, destroy, and merge operations.

Execution requires a user-owned injected executor. Results preserve reported
output and usage. An unconfigured default executor fails explicitly.
Disabling the switch returns an explicit failed result.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import structlog

from app.core.metacognition.real_execution import (
    DEFAULT_EXECUTION_TIMEOUT,
    DEFAULT_MAX_OUTPUT_CHARS,
    SubTaskExecution,
    execute_subtask_llm,
    real_execution_enabled,
)

logger = structlog.get_logger(__name__)

# Executor contract: (goal, context) -> (output, tokens_used).
SubTaskExecutor = Callable[
    [str, dict[str, Any] | None], Awaitable[tuple[str, int] | SubTaskExecution]
]


class SubAgentState(StrEnum):
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
    source: str = "executor"
    status: str = "completed"


class SubAgentOrchestrator:
    """Manage hierarchical sub-agent lifecycle."""

    def __init__(
        self,
        max_agents: int = 10,
        max_depth: int = 3,
        executor: SubTaskExecutor | None = None,
        execution_timeout: float = DEFAULT_EXECUTION_TIMEOUT,
        max_output_chars: int = DEFAULT_MAX_OUTPUT_CHARS,
        token_budget: int = 8000,
    ):
        self._max_agents = max_agents
        self._max_depth = max_depth
        self._agents: dict[str, SubAgentTask] = {}
        self._active_count = 0
        self._executor = executor
        self._execution_timeout = execution_timeout
        self._max_output_chars = max_output_chars
        if min(max_agents, max_depth, execution_timeout, max_output_chars, token_budget) <= 0:
            raise ValueError("subagent limits must be positive")
        self._token_budget = token_budget
        self._tokens_used = 0
        self._running: dict[str, asyncio.Task] = {}

    def create_agent(
        self,
        goal: str,
        parent_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> SubAgentTask | None:
        """Create a new sub-agent if under limits."""
        if self._active_count >= self._max_agents:
            return None

        if parent_id is not None and parent_id not in self._agents:
            raise ValueError("unknown parent agent")
        depth = self._get_depth(parent_id) + 1
        if depth > self._max_depth:
            return None

        task_id = str(uuid.uuid4())[:8]
        agent = SubAgentTask(
            id=task_id,
            goal=goal,
            parent_id=parent_id,
            state=SubAgentState.PENDING,
            memory=dict(context or {}),
        )
        self._agents[task_id] = agent
        self._active_count += 1

        if parent_id and parent_id in self._agents:
            self._agents[parent_id].children.append(task_id)

        return agent

    async def dispatch(
        self,
        sub_tasks: list[dict[str, Any]],
        parent_id: str | None = None,
    ) -> list[DispatchResult]:
        """Dispatch multiple sub-tasks and collect results.

        Each sub-agent runs for real through the configured executor (or
        the default bounded LLM turn). Awaiting this method is required.
        """
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
            else:
                results.append(
                    DispatchResult(
                        "",
                        False,
                        "failed: agent limit exceeded",
                        0,
                        status="failed",
                        source="unexecuted",
                    )
                )

        # Real execution (bounded, with fallback)
        try:
            for agent in agents:
                results.append(await self._execute_agent(agent))
        finally:
            for agent in agents:
                if agent.state == SubAgentState.PENDING:
                    agent.state = SubAgentState.CANCELLED
                    self._active_count -= 1

        return results

    async def _execute_agent(self, agent: SubAgentTask) -> DispatchResult:
        """Execute a single sub-agent with cost caps and failure fallback."""
        agent.state = SubAgentState.RUNNING

        try:
            if not real_execution_enabled():
                raise RuntimeError("real execution disabled")
            remaining = self._token_budget - self._tokens_used
            if remaining <= 0:
                raise RuntimeError("subagent token budget exhausted")
            executor: SubTaskExecutor = self._executor or self._default_executor
            context = {**agent.memory, "token_budget": remaining}
            running = asyncio.create_task(executor(agent.goal, context))
            self._running[agent.id] = running
            execution = await asyncio.wait_for(running, timeout=self._execution_timeout)
            if isinstance(execution, SubTaskExecution):
                output, tokens_used = execution.output, execution.tokens_used
                iterations = execution.iterations
                source = execution.source
            else:
                output, tokens_used = execution
                iterations, source = 1, "injected_executor" if self._executor else "llm_turn"
            if type(tokens_used) is not int or tokens_used < 0 or iterations < 0:
                raise ValueError("executor returned invalid usage")
            agent.tokens_used = tokens_used
            agent.iterations = iterations
            self._tokens_used += tokens_used
            if tokens_used > remaining:
                raise RuntimeError("subagent token budget exceeded")
            if isinstance(execution, SubTaskExecution) and (
                execution.status != "completed" or execution.error
            ):
                raise RuntimeError(execution.error or execution.status)
            if not isinstance(output, str) or not output.strip():
                raise ValueError("executor returned empty or invalid output")
        except asyncio.CancelledError:
            agent.state = SubAgentState.CANCELLED
            agent.result = "cancelled"
            raise
        except Exception as exc:
            reason = str(exc) or type(exc).__name__
            agent.state = SubAgentState.FAILED
            agent.result = f"failed: {type(exc).__name__}: {reason}"
            logger.warning("sub_agent_fallback", task_id=agent.id, reason=reason)
            return DispatchResult(
                task_id=agent.id,
                success=False,
                result=agent.result,
                tokens_used=agent.tokens_used,
                status="failed",
                source="unexecuted" if agent.iterations == 0 else "executor",
            )
        finally:
            self._running.pop(agent.id, None)
            self._active_count -= 1

        agent.state = SubAgentState.COMPLETED
        agent.result = output.strip()[: self._max_output_chars]

        return DispatchResult(
            task_id=agent.id,
            success=True,
            result=agent.result,
            tokens_used=agent.tokens_used,
            source=source,
        )

    async def _default_executor(self, goal: str, context: dict[str, Any] | None) -> tuple[str, int]:
        """Fail closed until the owning application injects an executor."""
        return await execute_subtask_llm(goal, context)

    def cancel_agent(self, task_id: str) -> bool:
        """Cancel a running sub-agent."""
        agent = self._agents.get(task_id)
        if not agent or agent.state != SubAgentState.RUNNING:
            return False
        running = self._running.get(task_id)
        if running is not None:
            running.cancel()
        for child in agent.children:
            self.cancel_agent(child)
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
            merged["results"].append(
                {
                    "id": agent.id,
                    "goal": agent.goal,
                    "state": agent.state.value,
                    "result": agent.result,
                }
            )

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
        for running in self._running.values():
            running.cancel()
        if self._running:
            raise RuntimeError("await cancelled dispatches before resetting")
        self._agents.clear()
        self._active_count = 0
        self._tokens_used = 0
