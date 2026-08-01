"""Periodic planning for complex tasks.

Provides planning capabilities that allow the agent to break down complex
tasks into manageable steps and adapt the plan based on execution results.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

import structlog

logger = structlog.get_logger()


class PlanStatus(str, Enum):
    """Status of a plan step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanStep(BaseModel):
    """A single step in a plan."""
    description: str
    status: str = Field(default=PlanStatus.PENDING.value)
    result: Any = None
    error: str | None = None
    step_index: int = 0

    def mark_completed(self, result: Any = None) -> None:
        self.status = PlanStatus.COMPLETED.value
        self.result = result

    def mark_failed(self, error: str) -> None:
        self.status = PlanStatus.FAILED.value
        self.error = error

    def mark_in_progress(self) -> None:
        self.status = PlanStatus.IN_PROGRESS.value

    def mark_skipped(self) -> None:
        self.status = PlanStatus.SKIPPED.value


class Plan(BaseModel):
    """A complete plan consisting of multiple steps."""
    task: str
    steps: list[PlanStep] = Field(default_factory=list)
    current_step: int = 0

    @property
    def is_complete(self) -> bool:
        return all(
            s.status in (PlanStatus.COMPLETED.value, PlanStatus.SKIPPED.value)
            for s in self.steps
        )

    @property
    def has_failures(self) -> bool:
        return any(s.status == PlanStatus.FAILED.value for s in self.steps)

    def get_next_pending(self) -> PlanStep | None:
        for step in self.steps:
            if step.status == PlanStatus.PENDING.value:
                return step
        return None

    def to_context(self) -> dict[str, Any]:
        """Convert plan to context dict for LLM prompts."""
        return {
            "task": self.task,
            "total_steps": len(self.steps),
            "current_step": self.current_step,
            "steps": [
                {
                    "index": i,
                    "description": s.description,
                    "status": s.status,
                    "result": str(s.result)[:200] if s.result else None,
                    "error": s.error,
                }
                for i, s in enumerate(self.steps)
            ],
        }


class Planner:
    """Periodic planning for complex tasks.

    Creates and updates plans based on task requirements and execution
    results. Integrates with the CodeAgent to provide structured task
    decomposition.
    """

    def __init__(
        self,
        model: Any = None,
        max_steps: int = 10,
        enable_replanning: bool = True,
    ):
        self.model = model
        self.max_steps = max_steps
        self.enable_replanning = enable_replanning

    async def create_plan(self, task: str, context: dict[str, Any] | None = None) -> Plan:
        """Create a step-by-step plan for the given task.

        If a model is available, uses LLM to generate the plan.
        Otherwise, creates a simple single-step plan.
        """
        if self.model is not None:
            return await self._create_plan_with_model(task, context)

        return Plan(
            task=task,
            steps=[PlanStep(description=task, step_index=0)],
        )

    async def _create_plan_with_model(
        self, task: str, context: dict[str, Any] | None
    ) -> Plan:
        """Use the model to generate a structured plan."""
        system_prompt = self._get_planning_system_prompt()
        user_message = self._format_planning_request(task, context)

        try:
            response = await self.model.chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ])

            content = response if isinstance(response, str) else getattr(response, "content", str(response))
            steps = self._parse_plan_response(content)

            if not steps:
                steps = [task]

        except Exception as e:
            logger.warning("planner.model_error", error=str(e))
            steps = [task]

        return Plan(
            task=task,
            steps=[
                PlanStep(description=s, step_index=i)
                for i, s in enumerate(steps[: self.max_steps])
            ],
        )

    async def update_plan(
        self,
        plan: Plan,
        step_index: int,
        result: Any,
        error: str | None = None,
    ) -> Plan:
        """Update plan based on execution result."""
        if step_index < len(plan.steps):
            step = plan.steps[step_index]
            if error:
                step.mark_failed(error)
            else:
                step.mark_completed(result)

        if self.enable_replanning and error and self.model is not None:
            return await self._replan_after_failure(plan, step_index, error)

        return plan

    async def _replan_after_failure(
        self, plan: Plan, failed_step: int, error: str
    ) -> Plan:
        """Attempt to replan after a step failure."""
        context = plan.to_context()
        context["failed_step"] = failed_step
        context["error"] = error

        try:
            response = await self.model.chat([
                {"role": "system", "content": self._get_replanning_system_prompt()},
                {"role": "user", "content": str(context)},
            ])

            content = response if isinstance(response, str) else getattr(response, "content", str(response))
            new_steps = self._parse_plan_response(content)

            if new_steps:
                existing = plan.steps[:failed_step]
                new_plan_steps = [
                    PlanStep(description=s, step_index=i + failed_step)
                    for i, s in enumerate(new_steps[: self.max_steps])
                ]
                plan.steps = existing + new_plan_steps

        except Exception as e:
            logger.warning("planner.replan_error", error=str(e))

        return plan

    def _get_planning_system_prompt(self) -> str:
        return (
            "You are a planning assistant. Given a task, break it down into "
            "a numbered list of clear, actionable steps. Each step should be "
            "a single sentence describing one action. Return ONLY the numbered "
            "list, one step per line. Maximum 10 steps.\n\n"
            "Example:\n"
            "1. Search for relevant information\n"
            "2. Analyze the search results\n"
            "3. Synthesize findings into a summary"
        )

    def _get_replanning_system_prompt(self) -> str:
        return (
            "You are a replanning assistant. A step in the plan has failed. "
            "Suggest alternative steps to achieve the original task. "
            "Return ONLY a numbered list of steps, one per line."
        )

    def _format_planning_request(
        self, task: str, context: dict[str, Any] | None
    ) -> str:
        msg = f"Task: {task}\n\n"
        if context:
            msg += f"Context: {context}\n\n"
        msg += "Please break this task into actionable steps."
        return msg

    def _parse_plan_response(self, response: str) -> list[str]:
        """Parse numbered list from model response."""
        steps = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # Remove numbering like "1.", "1)", "-", "*"
            cleaned = line
            for prefix in ("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "10."):
                if cleaned.startswith(prefix):
                    cleaned = cleaned[len(prefix):].strip()
                    break
            for prefix in ("1)", "2)", "3)", "4)", "5)", "6)", "7)", "8)", "9)", "10)"):
                if cleaned.startswith(prefix):
                    cleaned = cleaned[len(prefix):].strip()
                    break
            if cleaned.startswith("-") or cleaned.startswith("*"):
                cleaned = cleaned[1:].strip()
            if cleaned and not cleaned.startswith("#"):
                steps.append(cleaned)
        return steps
