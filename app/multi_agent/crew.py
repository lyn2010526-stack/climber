"""Crew orchestrator for multi-agent collaboration."""

from __future__ import annotations

from typing import Any

import structlog

from app.core import AgentEventType
from app.core.agent_engine import AgentEngine
from app.multi_agent import AgentRole, AgentTask, CrewOutput, TaskStatus

logger = structlog.get_logger()


class Crew:
    """Orchestrates multiple agents working together on tasks."""

    def __init__(
        self,
        agents: list[AgentRole],
        tasks: list[AgentTask],
        engine: AgentEngine,
        max_iterations: int = 10,
        verbose: bool = True,
    ):
        self.crew_id = str(uuid.uuid4())[:8]
        self.agents = {a.name: a for a in agents}
        self.tasks = tasks
        self.engine = engine
        self.max_iterations = max_iterations
        self.verbose = verbose
        self._results: list[dict[str, Any]] = []
        self._iterations = 0

    async def execute(self, user_id: str = "system") -> CrewOutput:
        """Execute all tasks with the assigned agents."""
        context = self._build_initial_context()

        for task in self.tasks:
            self._iterations += 1
            if self._iterations > self.max_iterations:
                logger.warning("Max iterations reached", crew_id=self.crew_id)
                break

            agent = self.agents.get(task.agent_name)
            if not agent:
                task.status = TaskStatus.FAILED
                task.error = f"Agent '{task.agent_name}' not found"
                continue

            task.status = TaskStatus.RUNNING
            result = await self._execute_task(task, agent, context, user_id)
            task.result = result
            task.status = TaskStatus.COMPLETED

            self._results.append({
                "task_id": task.id,
                "agent": agent.name,
                "description": task.description,
                "result": result,
            })

            # Update context with this task's output
            context += f"\n\n--- {agent.name} Output ---\n{result}"

        final_output = self._results[-1]["result"] if self._results else ""

        return CrewOutput(
            crew_id=self.crew_id,
            results=self._results,
            final_output=final_output,
            total_iterations=self._iterations,
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

        # Create a temporary session for this task
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

        full_response_parts: list[str] = []

        async for event in self.engine.run(session, task_message):
            if event.type == AgentEventType.TEXT:
                full_response_parts.append(event.data.get("content", ""))

        return "".join(full_response_parts)

    def _build_agent_system_prompt(self, agent: AgentRole, context: str) -> str:
        """Build system prompt for an agent."""
        return (
            f"You are {agent.name}, {agent.role}.\n"
            f"Your goal: {agent.goal}\n"
            f"Background: {agent.backstory}\n\n"
            f"## Context from previous tasks\n{context}\n\n"
            f"Focus only on your assigned task. Be thorough and specific."
        )

    def _build_task_message(self, task: AgentTask, context: str) -> str:
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


import uuid  # noqa: E402
