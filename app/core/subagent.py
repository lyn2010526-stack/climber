"""Sub-agent support — Agent can delegate tasks to child agents.

Inspired by CrewAI's hierarchical process and AutoGen's agent delegation.
A parent agent can spawn sub-agents for parallel or specialized work,
then aggregate their results.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

import structlog

from app.core import (
    AgentEvent,
    AgentEventType,
    SubAgentTask,
)
from app.core.agent_engine import AgentEngine
from app.models.registry import ModelRegistry
from app.tools import ToolRegistry

logger = structlog.get_logger()


class SubAgentResult:
    """Result from a sub-agent execution."""

    def __init__(
        self,
        task_id: str,
        success: bool,
        output: str,
        duration_ms: float,
        error: str | None = None,
        tokens_used: int = 0,
    ):
        self.task_id = task_id
        self.success = success
        self.output = output
        self.duration_ms = duration_ms
        self.error = error
        self.tokens_used = tokens_used

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "success": self.success,
            "output": self.output,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "tokens_used": self.tokens_used,
        }


class SubAgentRunner:
    """Manages spawning and coordinating sub-agents.

    Sub-agents are lightweight agents that:
    - Run in isolation with their own context
    - Can use different models than the parent
    - Return structured results to the parent
    - Support parallel execution for independent tasks
    """

    def __init__(
        self,
        engine: AgentEngine,
        model_registry: ModelRegistry,
        tool_registry: ToolRegistry,
    ):
        self._engine = engine
        self._model_registry = model_registry
        self._tool_registry = tool_registry

    async def run_single(
        self,
        task: SubAgentTask,
        stream_callback: Any = None,
    ) -> SubAgentResult:
        """Run a single sub-agent task and return the result."""
        start = time.monotonic()
        try:
            session = self._engine.create_session(
                agent_id=f"subagent-{task.task_id}",
                user_id="system",
                provider=task.provider,
                model_id=task.model_id,
                api_key=task.api_key,
                base_url=task.base_url,
                system_prompt=task.system_prompt,
                tools=task.tools,
            )

            full_output = ""
            tokens_used = 0

            async for event in self._engine.run(session, task.description):
                if event.type == AgentEventType.TEXT:
                    full_output += event.data.get("content", "")
                elif event.type == AgentEventType.DONE:
                    tokens_used = event.data.get("tokens_used", 0)
                elif event.type == AgentEventType.ERROR:
                    duration = (time.monotonic() - start) * 1000
                    return SubAgentResult(
                        task_id=task.task_id,
                        success=False,
                        output="",
                        duration_ms=duration,
                        error=event.data.get("error", "Unknown error"),
                    )

            duration = (time.monotonic() - start) * 1000
            return SubAgentResult(
                task_id=task.task_id,
                success=True,
                output=full_output,
                duration_ms=duration,
                tokens_used=tokens_used,
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            logger.error("Sub-agent failed", task_id=task.task_id, error=str(e))
            return SubAgentResult(
                task_id=task.task_id,
                success=False,
                output="",
                duration_ms=duration,
                error=str(e),
            )

    async def run_parallel(
        self,
        tasks: list[SubAgentTask],
        max_concurrency: int = 3,
    ) -> list[SubAgentResult]:
        """Run multiple sub-agent tasks in parallel."""
        semaphore = asyncio.Semaphore(max_concurrency)

        async def bounded_run(task: SubAgentTask) -> SubAgentResult:
            async with semaphore:
                return await self.run_single(task)

        return await asyncio.gather(*[bounded_run(t) for t in tasks])

    async def run_sequential(
        self,
        tasks: list[SubAgentTask],
    ) -> list[SubAgentResult]:
        """Run sub-agent tasks one by one, passing context forward."""
        results: list[SubAgentResult] = []
        accumulated_context = ""

        for task in tasks:
            if accumulated_context:
                task.description = (
                    f"{task.description}\n\nContext from previous steps:\n{accumulated_context}"
                )
            result = await self.run_single(task)
            results.append(result)
            if result.success:
                accumulated_context += f"\n---\n{result.output}"
            else:
                break  # Stop chain on failure

        return results

    async def run_with_stream(
        self,
        task: SubAgentTask,
    ) -> AsyncIterator[AgentEvent]:
        """Run a sub-agent with streaming events back to the parent."""
        yield AgentEvent(
            type=AgentEventType.SUB_AGENT_START,
            data={"task_id": task.task_id, "description": task.description},
        )

        result = await self.run_single(task)

        yield AgentEvent(
            type=AgentEventType.SUB_AGENT_END,
            data=result.to_dict(),
        )
