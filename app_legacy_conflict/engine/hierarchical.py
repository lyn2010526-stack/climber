"""Hierarchical multi-agent orchestration with manager-based task coordination.

Inspired by CrewAI's hierarchical process: a manager agent plans, assigns,
and verifies tasks, delegating execution to specialized worker agents.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

from app.multi_agent import AgentRole, AgentTask, CrewOutput, TaskStatus

logger = structlog.get_logger()


class TaskAssignment(BaseModel):
    """A task assignment produced by the manager's planning phase."""

    task_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_name: str
    description: str
    expected_output: str
    context: str = ""
    priority: int = 0
    dependencies: list[str] = Field(default_factory=list)
    guardrails: list[dict[str, Any]] = Field(default_factory=list)


class AgentSpec(BaseModel):
    """Extended agent specification for hierarchical crews."""

    name: str
    role: str
    goal: str
    backstory: str
    tools: list[str] = Field(default_factory=list)
    can_delegate: bool = True
    max_retries: int = 2
    metadata: dict[str, Any] = Field(default_factory=dict)


class VerificationResult(BaseModel):
    """Result of manager verification."""

    passed: bool
    feedback: str = ""
    needs_revision: bool = False


class ManagerAgent:
    """Manager that plans, assigns, and verifies tasks.

    The manager uses an LLM to:
    1. Analyze the overall task and create an execution plan
    2. Assign subtasks to appropriate agents based on capabilities
    3. Verify completed work meets requirements
    """

    def __init__(
        self,
        name: str = "Manager",
        llm_client: Any = None,
        max_verification_rounds: int = 3,
    ):
        self.name = name
        self.llm_client = llm_client
        self.max_verification_rounds = max_verification_rounds
        self._plan_history: list[dict[str, Any]] = []

    async def plan(self, task: str, agents: list[AgentSpec]) -> list[TaskAssignment]:
        """Create execution plan based on agent capabilities.

        Analyzes the task and produces a list of TaskAssignment objects
        that distribute work across available agents.
        """
        if not agents:
            raise ValueError("Cannot plan without agents")

        agent_descriptions = "\n".join(
            f"- {a.name} ({a.role}): Goal={a.goal}, Tools={a.tools}"
            for a in agents
        )

        prompt = (
            f"You are a project manager. Break the following task into subtasks "
            f"assigned to the most suitable agents.\n\n"
            f"## Task\n{task}\n\n"
            f"## Available Agents\n{agent_descriptions}\n\n"
            f"Return a JSON array of assignments. Each assignment should have:\n"
            f"- agent_name: which agent handles this\n"
            f"- description: clear, specific subtask description\n"
            f"- expected_output: what the agent should produce\n"
            f"- context: any additional context needed\n"
            f"- priority: integer (0=highest)\n"
            f"- dependencies: list of task_ids that must complete first\n\n"
            f"Return ONLY valid JSON, no markdown fences."
        )

        logger.info("manager_planning", task=task[:100], agent_count=len(agents))

        if self.llm_client is not None:
            response = await self._call_llm(prompt)
            assignments = self._parse_plan_response(response, agents)
        else:
            assignments = self._create_default_plan(task, agents)

        self._plan_history.append({
            "task": task,
            "assignments": [a.model_dump() for a in assignments],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

        logger.info("manager_plan_created", assignment_count=len(assignments))
        return assignments

    async def assign(self, assignment: TaskAssignment, agent: AgentRole, engine: Any, context: str, user_id: str) -> str:
        """Assign task to an agent and return result."""
        system_prompt = (
            f"You are {agent.name}, {agent.role}.\n"
            f"Your goal: {agent.goal}\n"
            f"Background: {agent.backstory}\n\n"
            f"## Context from previous tasks\n{context}\n\n"
            f"Focus only on your assigned task. Be thorough and specific."
        )

        session = engine.create_session(
            agent_id=f"hierarchical-{agent.name}-{uuid.uuid4().hex[:6]}",
            user_id=user_id,
            provider="openai",
            model_id="gpt-4",
            api_key="",
            system_prompt=system_prompt,
            tools=agent.tools,
        )

        task_message = f"## Your Task\n{assignment.description}\n"
        if assignment.expected_output:
            task_message += f"\n## Expected Output\n{assignment.expected_output}\n"
        if assignment.context:
            task_message += f"\n## Additional Context\n{assignment.context}\n"

        full_response_parts: list[str] = []

        async for event in engine.run(session, task_message):
            if event.type.value == "text":
                full_response_parts.append(event.data.get("content", ""))

        result = "".join(full_response_parts)
        logger.info(
            "manager_task_assigned",
            agent=agent.name,
            task_id=assignment.task_id,
            result_length=len(result),
        )
        return result

    async def verify(self, task: str, result: str) -> VerificationResult:
        """Verify task result meets requirements.

        Uses LLM-based verification when available, otherwise falls back
        to heuristic checks.
        """
        if not result or len(result.strip()) < 10:
            return VerificationResult(
                passed=False,
                feedback="Result is too short or empty. Please provide a more complete response.",
                needs_revision=True,
            )

        if self.llm_client is not None:
            prompt = (
                f"You are a quality assurance manager. Verify whether the following "
                f"result adequately addresses the original task.\n\n"
                f"## Original Task\n{task}\n\n"
                f"## Agent Result\n{result[:3000]}\n\n"
                f"Respond with JSON: {{\"passed\": boolean, \"feedback\": \"...\", \"needs_revision\": boolean}}"
            )
            response = await self._call_llm(prompt)
            return self._parse_verification_response(response)

        return VerificationResult(passed=True)

    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM client with a prompt."""
        if self.llm_client is None:
            return ""
        try:
            response = await self.llm_client.generate(prompt)
            return response
        except Exception as e:
            logger.error("manager_llm_call_failed", error=str(e))
            return ""

    def _parse_plan_response(self, response: str, agents: list[AgentSpec]) -> list[TaskAssignment]:
        """Parse LLM plan response into TaskAssignment objects."""
        import json

        agent_names = {a.name for a in agents}

        try:
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
            data = json.loads(cleaned)

            assignments = []
            for item in data:
                agent_name = item.get("agent_name", "")
                if agent_name not in agent_names:
                    logger.warning("plan_unknown_agent", agent=agent_name)
                    continue
                assignments.append(TaskAssignment(
                    agent_name=agent_name,
                    description=item.get("description", ""),
                    expected_output=item.get("expected_output", ""),
                    context=item.get("context", ""),
                    priority=item.get("priority", 0),
                    dependencies=item.get("dependencies", []),
                ))
            return assignments if assignments else self._create_default_plan("", agents)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("plan_parse_failed", error=str(e))
            return self._create_default_plan("", agents)

    def _parse_verification_response(self, response: str) -> VerificationResult:
        """Parse LLM verification response."""
        import json

        try:
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
            data = json.loads(cleaned)
            return VerificationResult(
                passed=data.get("passed", True),
                feedback=data.get("feedback", ""),
                needs_revision=data.get("needs_revision", False),
            )
        except (json.JSONDecodeError, KeyError):
            return VerificationResult(passed=True)

    def _create_default_plan(self, task: str, agents: list[AgentSpec]) -> list[TaskAssignment]:
        """Create a simple default plan when LLM is unavailable."""
        if not agents:
            return []
        primary = agents[0]
        return [TaskAssignment(
            agent_name=primary.name,
            description=task,
            expected_output="Complete the task thoroughly.",
        )]


class HierarchicalCrew:
    """Crew with hierarchical management.

    A manager agent plans the work, assigns tasks to worker agents,
    and verifies results before accepting them.
    """

    def __init__(
        self,
        agents: list[AgentSpec],
        manager: ManagerAgent | None = None,
        tasks: list[AgentTask] | None = None,
        engine: Any = None,
        max_iterations: int = 10,
        verbose: bool = True,
        user_id: str = "system",
    ):
        self.crew_id = str(uuid.uuid4())[:8]
        self.agents = {a.name: a for a in agents}
        self.manager = manager or ManagerAgent()
        self.tasks = tasks or []
        self.engine = engine
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.user_id = user_id
        self._results: list[dict[str, Any]] = []
        self._iterations = 0

    async def kickoff(self, task: str | None = None) -> CrewOutput:
        """Execute tasks with manager coordination.

        If a task string is provided, the manager first creates a plan.
        Otherwise, uses the pre-configured task list.
        """
        context = self._build_initial_context(task)

        if task:
            assignments = await self.manager.plan(task, list(self.agents.values()))
        else:
            assignments = [
                TaskAssignment(
                    agent_name=t.agent_name,
                    description=t.description,
                    expected_output=t.expected_output,
                    context=t.context,
                )
                for t in self.tasks
            ]

        completed: dict[str, str] = {}
        remaining = list(assignments)

        while remaining and self._iterations < self.max_iterations:
            ready = self._get_ready_tasks(remaining, completed)
            if not ready:
                logger.warning("hierarchical_deadlock", crew_id=self.crew_id)
                break

            batch_results = await asyncio.gather(
                *[self._execute_with_verification(a, context) for a in ready],
                return_exceptions=True,
            )

            for assignment, result in zip(ready, batch_results):
                if isinstance(result, Exception):
                    logger.error(
                        "hierarchical_task_failed",
                        task_id=assignment.task_id,
                        error=str(result),
                    )
                    completed[assignment.task_id] = f"ERROR: {result}"
                else:
                    completed[assignment.task_id] = result
                    self._results.append({
                        "task_id": assignment.task_id,
                        "agent": assignment.agent_name,
                        "description": assignment.description,
                        "result": result,
                    })
                    context += f"\n\n--- {assignment.agent_name} Output ---\n{result}"

                remaining.remove(assignment)
                self._iterations += 1

        final_output = self._results[-1]["result"] if self._results else ""

        return CrewOutput(
            crew_id=self.crew_id,
            results=self._results,
            final_output=final_output,
            total_iterations=self._iterations,
        )

    async def _execute_with_verification(self, assignment: TaskAssignment, context: str) -> str:
        """Execute a task with manager verification and retry logic."""
        agent_spec = self.agents.get(assignment.agent_name)
        if not agent_spec:
            raise ValueError(f"Agent '{assignment.agent_name}' not found")

        agent = AgentRole(
            name=agent_spec.name,
            role=agent_spec.role,
            goal=agent_spec.goal,
            backstory=agent_spec.backstory,
            tools=agent_spec.tools,
            can_delegate=agent_spec.can_delegate,
        )

        max_retries = agent_spec.max_retries
        last_result = ""

        for attempt in range(max_retries + 1):
            result = await self.manager.assign(
                assignment, agent, self.engine, context, self.user_id,
            )
            last_result = result

            verification = await self.manager.verify(assignment.description, result)
            if verification.passed:
                if self.verbose:
                    logger.info(
                        "task_verified",
                        task_id=assignment.task_id,
                        attempt=attempt + 1,
                    )
                return result

            if self.verbose:
                logger.info(
                    "task_needs_revision",
                    task_id=assignment.task_id,
                    attempt=attempt + 1,
                    feedback=verification.feedback,
                )

            if attempt < max_retries:
                assignment = TaskAssignment(
                    agent_name=assignment.agent_name,
                    description=assignment.description,
                    expected_output=assignment.expected_output,
                    context=assignment.context + f"\n\nRevision feedback: {verification.feedback}",
                    priority=assignment.priority,
                    dependencies=assignment.dependencies,
                )

        return last_result

    def _get_ready_tasks(
        self, remaining: list[TaskAssignment], completed: dict[str, str],
    ) -> list[TaskAssignment]:
        """Get tasks whose dependencies are all completed."""
        ready = []
        for task in remaining:
            if all(dep in completed for dep in task.dependencies):
                ready.append(task)
        ready.sort(key=lambda t: t.priority)
        return ready

    def _build_initial_context(self, task: str | None) -> str:
        """Build initial context for the crew."""
        if task:
            return f"## Overall Task\n{task}\n\n## Agent Roster\n" + "\n".join(
                f"- {a.name} ({a.role}): {a.goal}" for a in self.agents.values()
            )
        lines = ["## Task Plan"]
        for i, t in enumerate(self.tasks, 1):
            agent = self.agents.get(t.agent_name)
            role = agent.role if agent else "Unknown"
            lines.append(f"{i}. [{t.agent_name} - {role}]: {t.description}")
        return "\n".join(lines)
