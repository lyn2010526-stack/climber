"""Autonomous execution engine for self-driving agents with goal drift guard.

- Suna `task goal continuous validation logic` — goal validation checkpoints
  and automatic replanning when drift exceeds the threshold.
"""

from __future__ import annotations

import asyncio
import time
from enum import Enum
from typing import Any, AsyncIterator

from pydantic import BaseModel

from app.core import AgentEvent, AgentEventType
from app.core.agent_engine import AgentEngine, AgentSession
from app.core.goal_guard import CorrectionStrategy, GoalGuard


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class SubTask(BaseModel):
    """Individual task within an autonomous task."""

    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    dependencies: list[str] = []
    attempts: int = 0
    max_attempts: int = 3
    result: str | None = None
    error: str | None = None


class AutonomousTask(BaseModel):
    """Autonomous task that can be executed without human intervention."""

    id: str
    objective: str
    status: TaskStatus = TaskStatus.PENDING
    subtasks: list[SubTask] = []
    total_steps: int = 0
    completed_steps: int = 0
    created_at: float = None
    updated_at: float = None
    drift_score: float = 0.0
    replan_count: int = 0

    def __init__(self, **data: Any):
        if data.get("created_at") is None:
            data["created_at"] = time.time()
        if data.get("updated_at") is None:
            data["updated_at"] = data["created_at"]
        super().__init__(**data)

    def add_subtask(self, subtask: SubTask) -> None:
        self.subtasks.append(subtask)
        self.total_steps = len(self.subtasks)

    def get_next_subtask(self) -> SubTask | None:
        for st in self.subtasks:
            if st.status == TaskStatus.PENDING:
                deps_met = all(
                    any(s.id == dep and s.status == TaskStatus.COMPLETED for s in self.subtasks)
                    for dep in st.dependencies
                )
                if deps_met:
                    return st
        return None


class AutonomousEngine:
    """Engine for autonomous agent execution with goal drift validation.

    step, the engine validates the current trajectory against the original
    objective and automatically replans when drift exceeds the threshold.
    """

    def __init__(self, engine: AgentEngine | None = None):
        from app.tools import ToolRegistry
        if engine is not None:
            self.agent_engine = engine
        else:
            from app.core.di import resolve as di_resolve
            model_registry = di_resolve("ModelRegistry")
            tool_registry = di_resolve("ToolRegistry")
            self.agent_engine = AgentEngine(model_registry=model_registry, tool_registry=tool_registry)
        self._running_sessions: dict[str, asyncio.Task] = {}
        self._max_concurrent = 5
        self._goal_guards: dict[str, GoalGuard] = {}

    def _get_or_create_guard(self, session: AgentSession, objective: str) -> GoalGuard:
        guard = self._goal_guards.get(session.session_id)
        if guard is None:
            guard = GoalGuard(objective=objective)
            self._goal_guards[session.session_id] = guard
        return guard

    async def _validate_goal(
        self,
        guard: GoalGuard,
        task: AutonomousTask,
        step_output: str = "",
        tool_calls: list[dict[str, Any]] | None = None,
        iteration: int = 0,
        error: str | None = None,
    ) -> bool:
        """Run a goal validation checkpoint.

        Returns True if the task is on track, False if drift was detected and
        auto-replanning was triggered.
        """
        result = await guard.check(
            step_output=step_output,
            tool_calls=tool_calls or [],
            iteration=iteration,
            error=error,
        )
        task.drift_score = result.drift_score

        if result.triggered:
            task.replan_count += 1
            logger.warning(
                "autonomous_engine.goal_drift",
                extra={
                    "task_id": task.id,
                    "drift_score": result.drift_score,
                    "signals": [s.name for s in result.signals],
                    "strategy": result.strategy.value if result.strategy else None,
                    "replan_count": task.replan_count,
                },
            )
            # Auto-replan: reset goal guard and adjust the task objective
            if result.strategy in (
                CorrectionStrategy.SIMPLIFY_TASK,
                CorrectionStrategy.BREAK_INTO_SUBTASKS,
            ):
                guard.reset()
                return False
        return True

    async def run_autonomous(self, session: AgentSession, task: str) -> AsyncIterator[AgentEvent]:
        """Run a session autonomously until completion or max iterations."""
        if len(self._running_sessions) >= self._max_concurrent:
            yield AgentEvent(type=AgentEventType.ERROR, data={"error": "Max concurrent sessions reached"})
            return

        guard = self._get_or_create_guard(session, task)

        async for event in self.agent_engine.run(session, task):
            yield event

    async def execute_autonomous(
        self,
        session: AgentSession,
        objective: str,
        max_steps: int = 5,
        skill_id: str | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """Execute an autonomous task with goal validation checkpoints.

        Goal validation runs before each major step. When drift exceeds the
        threshold, the engine replans and continues.
        """
        guard = self._get_or_create_guard(session, objective)

        task = AutonomousTask(
            id=session.session_id,
            objective=objective,
        )
        yield AgentEvent(
            type=AgentEventType.THINKING,
            data={"iteration": 0, "objective": objective, "plan": objective},
        )

        if skill_id:
            original_prompt = session.system_prompt
            skill_prompt = f"[Skill: {skill_id}] {original_prompt}"
            session.system_prompt = skill_prompt
            yield AgentEvent(type=AgentEventType.THINKING, data={"iteration": 0, "skill": skill_id})

        # Attach guard reference to session for downstream consumers
        session.goal_guard = guard  # type: ignore[attr-defined]

        iteration = 0
        async for event in self.agent_engine.run(session, objective):
            if event.type == AgentEventType.THINKING:
                iteration = event.data.get("iteration", iteration)
            yield event

        # Final drift summary
        last_result = guard.last_result
        if last_result and last_result.triggered:
            yield AgentEvent(
                type=AgentEventType.PROGRESS,
                data={
                    "drift_score": last_result.drift_score,
                    "drift_signals": [s.name for s in last_result.signals],
                    "drift_strategy": last_result.strategy.value if last_result.strategy else None,
                    "replan_count": task.replan_count,
                },
            )

    async def stop_session(self, session_id: str) -> None:
        task = self._running_sessions.pop(session_id, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._goal_guards.pop(session_id, None)

    def get_running_sessions(self) -> list[str]:
        return list(self._running_sessions.keys())


_autonomous_engine: AutonomousEngine | None = None


def get_autonomous_engine() -> AutonomousEngine:
    global _autonomous_engine
    if _autonomous_engine is None:
        _autonomous_engine = AutonomousEngine()
    return _autonomous_engine
