# app/engine/multi_agent.py
"""Multi-agent collaboration orchestrator.

Three modes:
- fork: spawn a single sub-agent for a sub-task (serial)
- coordinate: dispatch multiple workers in parallel (parallel)
- team: role-based collaboration with verification (agent teams)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SubTask:
    task_id: str
    description: str
    context: dict[str, Any] = field(default_factory=dict)
    assigned_role: str = "general"
    result: Any = None
    success: bool = False


@dataclass
class ForkResult:
    success: bool
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0


class MultiAgentOrchestrator:
    """Coordinates sub-agents in fork/coordinate/team patterns."""

    def __init__(self, engine):
        self.engine = engine
        self._semaphore = asyncio.Semaphore(5)

    async def fork(self, task: str, context: dict | None = None, agent_id: str = "") -> ForkResult:
        """Spawn a single sub-agent for a sub-task."""
        import time
        start = time.monotonic()
        async with self._semaphore:
            session = await self.engine.create_session(
                agent_id=agent_id or "subagent",
                user_id=context.get("user_id", "local") if context else "local",
            )
            events = []
            async for event in self.engine.run(session, task):
                events.append(event)
            text_events = [e for e in events if hasattr(e, 'type') and e.type == "TEXT"]
            output = text_events[-1].data.get("content", "") if text_events else ""
            return ForkResult(
                success=True, output=output,
                duration_ms=(time.monotonic() - start) * 1000,
            )

    async def coordinate(self, tasks: list[SubTask], max_concurrency: int = 3) -> list[SubTask]:
        """Dispatch multiple workers in parallel with bounded concurrency."""
        sem = asyncio.Semaphore(max_concurrency)

        async def _run(task: SubTask) -> SubTask:
            async with sem:
                result = await self.fork(
                    task=task.description,
                    context=task.context,
                )
                task.result = result.output
                task.success = result.success
                return task

        return await asyncio.gather(*[_run(t) for t in tasks])

    async def team(self, task: str, roles: list[str], context: dict | None = None) -> dict:
        """Role-based collaboration: planner -> worker -> reviewer."""
        ctx = context or {}
        # Phase 1: Planner breaks down the task
        plan_result = await self.fork(
            task=f"Break this task into actionable steps:\n{task}",
            context={**ctx, "role": "planner"},
        )
        if not plan_result.success:
            return {"success": False, "error": "Planning failed"}

        # Phase 2: Worker executes
        work_result = await self.fork(
            task=f"Execute this plan:\n{plan_result.output}\n\nOriginal task:\n{task}",
            context={**ctx, "role": "worker"},
        )
        if not work_result.success:
            return {"success": False, "error": "Execution failed", "plan": plan_result.output}

        # Phase 3: Reviewer validates
        review_result = await self.fork(
            task=f"Review this output for correctness and completeness:\n{work_result.output}\n\nOriginal task:\n{task}",
            context={**ctx, "role": "reviewer"},
        )
        return {
            "success": True,
            "plan": plan_result.output,
            "output": work_result.output,
            "review": review_result.output if review_result.success else "",
        }
