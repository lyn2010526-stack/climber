"""ReAct Planner — Reasoning + Acting loop with dynamic replanning.

Implements the ReAct (Reasoning + Acting) paradigm where the agent
alternates between reasoning about the situation and taking actions,
using observations to inform subsequent reasoning.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

import structlog

logger = structlog.get_logger()


class StepStatus(Enum):
    """Status of a ReAct step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Actionable(Protocol):
    """Protocol for action handlers."""

    async def execute(self, action: str, args: dict[str, Any]) -> dict[str, Any]: ...


@dataclass
class ReActStep:
    """A single step in the ReAct loop."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    thought: str = ""
    action: str | None = None
    action_args: dict[str, Any] = field(default_factory=dict)
    observation: str = ""
    status: StepStatus = StepStatus.PENDING
    step_number: int = 0

    def to_context(self) -> dict[str, Any]:
        """Convert to context dict for LLM prompt."""
        return {
            "id": self.id,
            "thought": self.thought,
            "action": self.action,
            "observation": self.observation,
            "status": self.status.value,
        }


@dataclass
class ReActResult:
    """Result of a complete ReAct planning session."""

    goal: str
    steps: list[ReActStep] = field(default_factory=list)
    final_answer: str = ""
    success: bool = False
    iterations_used: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def completed_steps(self) -> list[ReActStep]:
        return [s for s in self.steps if s.status == StepStatus.COMPLETED]

    @property
    def failed_steps(self) -> list[ReActStep]:
        return [s for s in self.steps if s.status == StepStatus.FAILED]

    def format_history(self) -> str:
        """Format step history for prompt injection."""
        lines: list[str] = []
        for step in self.steps:
            lines.append(f"Thought {step.step_number}: {step.thought}")
            if step.action:
                lines.append(f"Action {step.step_number}: {step.action}({step.action_args})")
            if step.observation:
                lines.append(f"Observation {step.step_number}: {step.observation}")
        return "\n".join(lines)


class ReActPlanner:
    """ReAct-based planner with dynamic replanning capabilities.

    The planner maintains a loop of:
    1. Think: Reason about current state
    2. Act: Choose and execute an action
    3. Observe: Process action results
    4. Re-evaluate: Adjust plan based on observations
    """

    def __init__(
        self,
        max_iterations: int = 10,
        action_handler: Actionable | None = None,
        early_termination: bool = True,
    ) -> None:
        self.max_iterations = max_iterations
        self.action_handler = action_handler
        self.early_termination = early_termination
        self._current_plan: ReActResult | None = None

    async def plan(
        self,
        goal: str,
        context: dict[str, Any] | None = None,
    ) -> ReActResult:
        """Generate an execution plan for the given goal.

        Args:
            goal: The objective to achieve.
            context: Additional context for planning.

        Returns:
            ReActResult with the execution plan.
        """
        result = ReActResult(goal=goal, metadata=context or {})
        self._current_plan = result

        logger.info("react_plan_started", goal=goal, max_iterations=self.max_iterations)

        for iteration in range(1, self.max_iterations + 1):
            result.iterations_used = iteration

            step = await self._generate_thought(goal, result, iteration)
            step.step_number = iteration
            result.steps.append(step)

            if self._should_terminate(result):
                step.status = StepStatus.COMPLETED
                result.success = True
                result.final_answer = step.thought
                logger.info("react_plan_completed", iterations=iteration)
                break

            if self.action_handler and step.action:
                step.status = StepStatus.IN_PROGRESS
                try:
                    obs = await self.action_handler.execute(step.action, step.action_args)
                    step.observation = str(obs.get("result", obs))
                    step.status = StepStatus.COMPLETED
                except Exception as e:
                    step.observation = f"Error: {e}"
                    step.status = StepStatus.FAILED
                    logger.warning("react_step_failed", iteration=iteration, error=str(e))
            else:
                step.status = StepStatus.COMPLETED

        if not result.success and result.iterations_used >= self.max_iterations:
            result.final_answer = self._synthesize_partial_result(result)
            logger.info("react_plan_max_iterations", iterations=result.iterations_used)

        return result

    async def execute_step(
        self,
        goal: str,
        step: ReActStep,
        history: list[ReActStep],
    ) -> ReActStep:
        """Execute a single ReAct step.

        Args:
            goal: The overall goal.
            step: The step to execute.
            history: Previous steps for context.

        Returns:
            The executed step with observation filled.
        """
        step.status = StepStatus.IN_PROGRESS

        if self.action_handler and step.action:
            try:
                result = await self.action_handler.execute(step.action, step.action_args)
                step.observation = str(result.get("result", result))
                step.status = StepStatus.COMPLETED
            except Exception as e:
                step.observation = f"Error: {e}"
                step.status = StepStatus.FAILED

        return step

    async def replan(
        self,
        result: ReActResult,
        feedback: str,
    ) -> ReActStep:
        """Generate a new step based on feedback and current state.

        Args:
            result: Current plan execution result.
            feedback: Feedback to incorporate.

        Returns:
            A new ReActStep adjusted based on feedback.
        """
        last_step = result.steps[-1] if result.steps else None

        new_step = ReActStep(
            step_number=len(result.steps) + 1,
            thought=f"Adjusting based on feedback: {feedback}",
        )

        if last_step and last_step.status == StepStatus.FAILED:
            new_step.thought = f"Previous action failed. Trying alternative approach."
            new_step.action = "retry_with_adjustment"
            new_step.action_args = {"original_action": last_step.action, "feedback": feedback}

        logger.info("react_replan_triggered", step_number=new_step.step_number)
        return new_step

    def _should_terminate(self, result: ReActResult) -> bool:
        """Check if planning should terminate early."""
        if not self.early_termination:
            return False

        if not result.steps:
            return False

        last = result.steps[-1]

        if last.observation and self._is_satisficing(last.observation):
            return True

        if last.thought and self._indicates_completion(last.thought):
            return True

        if len(result.failed_steps) > len(result.steps) // 2:
            return True

        return False

    async def _generate_thought(
        self,
        goal: str,
        result: ReActResult,
        iteration: int,
    ) -> ReActStep:
        """Generate the next thought step based on current state."""
        history = result.format_history()

        if iteration == 1:
            thought = f"Goal: {goal}. I need to break this down into actionable steps."
            action = "analyze_goal"
        elif result.failed_steps:
            last_failed = result.failed_steps[-1]
            thought = f"The previous action '{last_failed.action}' failed with: {last_failed.observation}. Let me try a different approach."
            action = "adjust_approach"
        else:
            thought = f"Progress so far: {len(result.completed_steps)} steps completed. Continuing toward goal."
            action = "continue_execution"

        return ReActStep(
            thought=thought,
            action=action,
            action_args={"iteration": iteration, "goal": goal, "history": history},
        )

    def _is_satisficing(self, observation: str) -> bool:
        """Check if observation indicates goal is satisfactorily met."""
        indicators = ["success", "completed", "done", "achieved", "finished"]
        obs_lower = observation.lower()
        return any(ind in obs_lower for ind in indicators)

    def _indicates_completion(self, thought: str) -> bool:
        """Check if thought indicates task completion."""
        completion_phrases = [
            "final answer",
            "task is complete",
            "objective achieved",
            "the answer is",
            "in conclusion",
        ]
        thought_lower = thought.lower()
        return any(phrase in thought_lower for phrase in completion_phrases)

    def _synthesize_partial_result(self, result: ReActResult) -> str:
        """Ssynthesize a final answer from partial progress."""
        completed = result.completed_steps
        if not completed:
            return f"Unable to complete goal: {result.goal}"

        summary_parts = [f"Partially completed ({len(completed)}/{len(result.steps)} steps):"]
        for step in completed:
            if step.observation:
                summary_parts.append(f"- {step.observation[:100]}")

        return "\n".join(summary_parts)
