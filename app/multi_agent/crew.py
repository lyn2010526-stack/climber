"""Crew orchestrator for multi-agent collaboration.

Scheduling references:

* LangGraph Send API: https://docs.langchain.com/oss/python/langgraph/use-graph-api
* AutoGen GroupChat: https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/selector-group-chat.html
* crewAI processes: https://docs.crewai.com/concepts/processes

This implementation uses bounded fan-out/fan-in for independent tasks. The
request-level crews API remains the sequential process when task output is
required as the next task's context.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import structlog

from app.core import AgentEventType
from app.multi_agent import AgentRole, AgentTask, CrewOutput, TaskStatus

if TYPE_CHECKING:
    from app.core.agent_engine import AgentEngine

logger = structlog.get_logger()

# Ceiling on crew tasks in flight at once. A crew task is a full agent turn
# (LLM call plus tool calls), so the tasks are I/O bound and the ceiling exists
# to protect the shared AgentEngine session registry and the upstream model
# provider rate limit, not the event loop. 5 matches SubagentManager's
# concurrency_limit and the TreeOf-Thought path cap.
DEFAULT_MAX_CONCURRENCY = 5


def _parse_max_concurrency(raw: Any) -> int:
    """Resolve the crew concurrency cap, falling back to the default on bad input.

    A malformed or non-positive value must never disable the cap and turn a crew
    into an unbounded fan-out, so anything unparsable or non-positive yields
    DEFAULT_MAX_CONCURRENCY. Mirrors ``agent_engine._parse_max_sessions``.

    Args:
        raw: The raw configuration value.

    Returns:
        A positive concurrency cap.
    """
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_MAX_CONCURRENCY
    if value <= 0:
        return DEFAULT_MAX_CONCURRENCY
    return value


def _resolve_max_concurrency() -> int:
    """Read the cap from the environment, once per crew execution.

    Reading it per run rather than at import time keeps a reconfigured
    environment (and a test) in charge of the value.

    Returns:
        The concurrency cap for the next wave.
    """
    return _parse_max_concurrency(
        os.environ.get("CLIMBER_CREW_MAX_CONCURRENCY", DEFAULT_MAX_CONCURRENCY)
    )


@dataclass
class _TaskOutcome:
    """What one task produced, resolved by the wave that ran it.

    The concurrent section only builds outcomes; mutating the shared
    ``AgentTask`` objects and the crew's result list happens afterwards, in one
    place, so no two in-flight tasks write the same state.
    """

    task: AgentTask
    agent: AgentRole
    result: str = ""
    error: str | None = None


class Crew:
    """Orchestrates multiple agents working together on tasks."""

    def __init__(
        self,
        agents: list[AgentRole],
        tasks: list[AgentTask],
        engine: AgentEngine,
        max_iterations: int = 10,
        max_concurrency: int | None = None,
        process: str = "sequential",
        verbose: bool = True,
    ):
        self.crew_id = str(uuid.uuid4())[:8]
        self.agents = {a.name: a for a in agents}
        self.tasks = tasks
        self.engine = engine
        self.max_iterations = max_iterations
        if process not in {"sequential", "parallel"}:
            raise ValueError("process must be 'sequential' or 'parallel'")
        self.process = process
        self.max_concurrency = (
            _parse_max_concurrency(max_concurrency) if max_concurrency is not None else None
        )
        self.verbose = verbose
        self._results: list[dict[str, Any]] = []
        self._iterations = 0

    async def execute(self, user_id: str = "system") -> CrewOutput:
        """Execute tasks with the configured sequential or parallel process.

        Scheduling follows the fan-out/fan-in shape the open-source engines
        converge on: LangGraph executes independent nodes in parallel and merges
        state at a step boundary, AutoGen GroupChat selects one speaker per
        turn, and crewAI's sequential process follows the declared task order.
        ``process="parallel"`` uses bounded fan-out/fan-in; the default
        ``process="sequential"`` passes each completed result forward.

        Parallel tasks receive the dispatch-time task plan and merge outputs in
        declaration order. Sequential tasks append each successful output to
        the next task's context. The request-level crews API also retains its
        existing sequential execution path.

        Failure isolation: one task raising does not stop the others. The
        failing task is marked ``FAILED`` with its error, the remaining tasks
        still contribute results, and the crew returns a partial success.
        Cancellation still propagates, so an aborted crew run does not look
        completed.

        Iteration budget: ``max_iterations`` caps dispatched tasks. Tasks past
        the cap stay ``PENDING`` and a warning is logged. A task whose
        ``agent_name`` matches no configured agent is marked ``FAILED`` before
        dispatch and costs no budget.

        Args:
            user_id: The user the sessions belong to.

        Returns:
            The crew output. ``results`` holds the successful tasks only, in
            declaration order; failed tasks carry their error on the
            ``AgentTask`` itself.
        """
        from app.core.observability.emergency_stop import execution_blocked

        blocked = execution_blocked()
        if blocked is not None:
            for task in self.tasks:
                task.status = TaskStatus.FAILED
                task.error = blocked
            return CrewOutput(
                crew_id=self.crew_id,
                results=[],
                final_output=blocked,
                total_iterations=0,
            )

        if not self.tasks:
            return CrewOutput(
                crew_id=self.crew_id,
                results=[],
                final_output="Crew has no tasks configured",
                total_iterations=0,
            )

        if self.process == "sequential":
            await self._run_sequential(user_id)
        else:
            context = self._build_initial_context()
            wave = self._select_wave()
            outcomes = await self._run_wave(wave, context, user_id)
            self._merge_wave(outcomes)

        final_output = self._results[-1]["result"] if self._results else ""

        return CrewOutput(
            crew_id=self.crew_id,
            results=self._results,
            final_output=final_output,
            total_iterations=self._iterations,
        )

    async def _run_sequential(self, user_id: str) -> None:
        """Run tasks in declaration order and pass each result forward."""
        context = self._build_initial_context()
        for task in self.tasks:
            agent = self.agents.get(task.agent_name)
            if agent is None:
                task.status = TaskStatus.FAILED
                task.error = f"Agent '{task.agent_name}' not found"
                logger.warning(
                    "crew_task_agent_missing",
                    crew_id=self.crew_id,
                    task_id=task.id,
                    agent=task.agent_name,
                )
                continue
            if self._iterations >= self.max_iterations:
                task.status = TaskStatus.PENDING
                continue

            self._iterations += 1
            task.status = TaskStatus.RUNNING
            try:
                result = await self._execute_task(task, agent, context, user_id)
            except asyncio.CancelledError:
                task.status = TaskStatus.PENDING
                raise
            except Exception as exc:
                task.status = TaskStatus.FAILED
                task.error = str(exc)
                logger.exception(
                    "crew_task_failed",
                    crew_id=self.crew_id,
                    task_id=task.id,
                    agent=agent.name,
                    error=str(exc),
                )
                continue

            task.result = result
            task.status = TaskStatus.COMPLETED
            self._results.append(
                {
                    "task_id": task.id,
                    "agent": agent.name,
                    "description": task.description,
                    "result": result,
                }
            )
            context += f"\n\n--- {agent.name} Output ---\n{result}"

        if any(task.status == TaskStatus.PENDING for task in self.tasks):
            logger.warning(
                "crew_max_iterations_reached",
                crew_id=self.crew_id,
                max_iterations=self.max_iterations,
            )

    def _select_wave(self) -> list[tuple[AgentTask, AgentRole]]:
        """Resolve the tasks to dispatch and apply the iteration budget.

        Tasks without a matching agent fail up front: the engine is never asked
        to run them, so they do not consume the iteration budget.

        Returns:
            The (task, agent) pairs to run, in task declaration order.
        """
        wave: list[tuple[AgentTask, AgentRole]] = []
        for task in self.tasks:
            agent = self.agents.get(task.agent_name)
            if agent is None:
                task.status = TaskStatus.FAILED
                task.error = f"Agent '{task.agent_name}' not found"
                logger.warning(
                    "crew_task_agent_missing",
                    crew_id=self.crew_id,
                    task_id=task.id,
                    agent=task.agent_name,
                )
                continue
            wave.append((task, agent))

        if len(wave) > self.max_iterations:
            logger.warning(
                "crew_max_iterations_reached",
                crew_id=self.crew_id,
                max_iterations=self.max_iterations,
                pending=len(wave) - self.max_iterations,
            )
            for task, _ in wave[self.max_iterations :]:
                task.status = TaskStatus.PENDING
            wave = wave[: self.max_iterations]

        self._iterations += len(wave)
        return wave

    async def _run_wave(
        self,
        wave: list[tuple[AgentTask, AgentRole]],
        context: str,
        user_id: str,
    ) -> list[_TaskOutcome]:
        """Run every task of the wave concurrently under a concurrency cap.

        The semaphore is the same gate AutoGen's Group Chat keeps on a single
        speaker: whatever the number of tasks, only ``CLIMBER_CREW_MAX_CONCURRENCY``
        of them may be in flight. ``asyncio.gather`` keeps the input order, so
        the returned outcomes are in declaration order.

        Args:
            wave: The (task, agent) pairs to run.
            context: The crew context handed to every task.
            user_id: The user the sessions belong to.

        Returns:
            One outcome per task, in declaration order.
        """
        if not wave:
            return []

        configured_concurrency = (
            self.max_concurrency if self.max_concurrency is not None else _resolve_max_concurrency()
        )
        max_concurrency = min(configured_concurrency, len(wave))
        semaphore = asyncio.Semaphore(max_concurrency)
        logger.info(
            "crew_wave_start",
            crew_id=self.crew_id,
            tasks=len(wave),
            max_concurrency=max_concurrency,
        )

        async def _run_one(task: AgentTask, agent: AgentRole) -> _TaskOutcome:
            async with semaphore:
                task.status = TaskStatus.RUNNING
                try:
                    result = await self._execute_task(task, agent, context, user_id)
                except Exception as exc:
                    logger.exception(
                        "crew_task_failed",
                        crew_id=self.crew_id,
                        task_id=task.id,
                        agent=agent.name,
                        error=str(exc),
                    )
                    return _TaskOutcome(task=task, agent=agent, error=str(exc))
                return _TaskOutcome(task=task, agent=agent, result=result)

        workers = [asyncio.create_task(_run_one(task, agent)) for task, agent in wave]
        try:
            outcomes = await asyncio.gather(*workers)
        except asyncio.CancelledError:
            for worker in workers:
                worker.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
            for task, _ in wave:
                if task.status == TaskStatus.RUNNING:
                    task.status = TaskStatus.PENDING
                    task.error = "Crew execution cancelled"
            raise
        logger.info(
            "crew_wave_done",
            crew_id=self.crew_id,
            completed=sum(1 for o in outcomes if o.error is None),
            failed=sum(1 for o in outcomes if o.error is not None),
        )
        return list(outcomes)

    def _merge_wave(self, outcomes: list[_TaskOutcome]) -> None:
        """Apply the wave's outcomes to the tasks and the crew result list.

        Args:
            outcomes: Outcomes in declaration order.
        """
        for outcome in outcomes:
            task = outcome.task
            if outcome.error is not None:
                task.status = TaskStatus.FAILED
                task.error = outcome.error
                continue

            task.result = outcome.result
            task.status = TaskStatus.COMPLETED
            self._results.append(
                {
                    "task_id": task.id,
                    "agent": outcome.agent.name,
                    "description": task.description,
                    "result": outcome.result,
                }
            )

    async def _execute_task(
        self,
        task: AgentTask,
        agent: AgentRole,
        context: str,
        user_id: str,
    ) -> str:
        """Execute a single task with an agent."""
        system_prompt = self._build_agent_system_prompt(agent, context)

        # Create a temporary session for this task. Two tasks for the same agent
        # in one wave get separate session ids, and AgentEngine locks per session
        # id, so the engine never sees the same session run twice concurrently.
        session = self.engine.create_session(
            agent_id=f"crew-{self.crew_id}-{agent.name}",
            user_id=user_id,
            provider="openai",
            model_id="gpt-4",
            api_key="",  # Will be set from request
            system_prompt=system_prompt,
            tools=agent.tools,
        )

        # Build the task message
        task_message = self._build_task_message(task, context)

        return "".join(
            [
                event.data.get("content", "")
                async for event in self.engine.run(session, task_message)
                if event.type == AgentEventType.TEXT
            ]
        )

    def _build_agent_system_prompt(self, agent: AgentRole, context: str) -> str:
        """Build system prompt for an agent."""
        return (
            f"You are {agent.name}, {agent.role}.\n"
            f"Your goal: {agent.goal}\n"
            f"Background: {agent.backstory}\n\n"
            f"## Context from previous tasks\n{context}\n\n"
            f"Focus only on your assigned task. Be thorough and specific."
        )

    def _build_task_message(self, task: AgentTask, _context: str) -> str:
        """Build the task message for the agent."""
        msg = f"## Your Task\n{task.description}\n"
        if task.expected_output:
            msg += f"\n## Expected Output\n{task.expected_output}\n"
        if task.context:
            msg += f"\n## Additional Context\n{task.context}\n"
        return msg

    def _build_initial_context(self) -> str:
        """Build the initial context from task descriptions."""
        lines = ["## Task Plan"]
        for i, task in enumerate(self.tasks, 1):
            agent = self.agents.get(task.agent_name)
            role = agent.role if agent else "Unknown"
            lines.append(f"{i}. [{task.agent_name} - {role}]: {task.description}")
        return "\n".join(lines)
