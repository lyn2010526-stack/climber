"""ReAct loop implementation with goal drift detection.

- AutoGPT `agent/` + ReAct pattern.
- Suna `task goal continuous validation logic` — GoalGuard integration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.core.goal_guard import CorrectionStrategy, GoalGuard

logger = logging.getLogger(__name__)


@dataclass
class ReActStep:
    thought: str
    action: str
    action_input: dict[str, Any]
    observation: str = ""
    done: bool = False
    drift_score: float = 0.0
    drift_triggered: bool = False
    correction_prompt: str = ""


class ReActAgent:
    """ReAct loop: Thought -> Action -> Observation with goal drift guard."""

    def __init__(self, engine: Any, tools: list[str] | None = None):
        self.engine = engine
        self.tools = tools or []
        self.max_steps = 10
        self.goal_guard: GoalGuard | None = None

    def set_objective(self, objective: str, threshold: float = 0.6) -> None:
        """Initialize the goal guard for this run."""
        self.goal_guard = GoalGuard(objective=objective, threshold=threshold)

    def _inject_correction(self, prompt: str, correction: str) -> str:
        """Inject a goal reminder at the top of the prompt."""
        if correction and correction not in prompt:
            return f"{correction}\n\n{prompt}"
        return prompt

    async def run(self, task: str, session: Any) -> dict[str, Any]:
        """Run the ReAct loop for a task with goal drift detection."""
        if self.goal_guard is None:
            self.goal_guard = GoalGuard(objective=task)

        steps: list[ReActStep] = []
        prompt = self._build_prompt(task, steps)
        completed_steps: list[dict[str, Any]] = []

        for step_num in range(self.max_steps):
            # Thought + Action
            response = await self._call_model(session, prompt)
            parsed = self._parse_response(response)
            if not parsed:
                break

            step = ReActStep(
                thought=parsed.get("thought", ""),
                action=parsed.get("action", ""),
                action_input=parsed.get("action_input", {}),
            )

            # Execute action
            if step.action.lower() in ("finish", "complete", "answer", "done"):
                step.observation = parsed.get("observation", "Task completed")
                step.done = True
                steps.append(step)
                completed_steps.append({
                    "action": step.action,
                    "observation": step.observation,
                })
                break

            observation = await self._execute_action(step.action, step.action_input)
            step.observation = observation

            # Goal drift check after this step
            drift_result = await self.goal_guard.check(
                step_output=step.thought + " " + step.observation,
                tool_calls=[{"function": {"name": step.action, "arguments": step.action_input}}],
                iteration=step_num + 1,
            )
            step.drift_score = drift_result.drift_score
            step.drift_triggered = drift_result.triggered
            step.correction_prompt = (
                self.goal_guard.build_correction_prompt(drift_result) if drift_result.triggered else ""
            )

            # Track drift score in session metadata
            if hasattr(session, "session_metadata"):
                session.session_metadata = getattr(session, "session_metadata", {})
                session.session_metadata["drift_score"] = drift_result.drift_score
                session.session_metadata["drift_signals"] = [s.name for s in drift_result.signals]
                session.session_metadata["drift_triggered"] = drift_result.triggered
                session.session_metadata["drift_strategy"] = (
                    drift_result.strategy.value if drift_result.strategy else None
                )

            if drift_result.triggered and drift_result.strategy == CorrectionStrategy.ASK_USER:
                step.observation += "\n[SYSTEM: Agent is off-track. User clarification may be needed.]"

            steps.append(step)
            completed_steps.append({
                "action": step.action,
                "observation": step.observation,
            })

            # Build next prompt, injecting correction if drift was detected
            prompt = self._build_prompt(task, steps)
            if step.correction_prompt:
                prompt = self._inject_correction(prompt, step.correction_prompt)

            # If repeated failures with simplify strategy, inject re-planning prompt
            if (
                drift_result.triggered
                and drift_result.strategy == CorrectionStrategy.SIMPLIFY_TASK
                and len(steps) >= 3
            ):
                replan = self.goal_guard.build_replan_prompt(completed_steps)
                prompt = self._inject_correction(prompt, replan)

        return {
            "output": steps[-1].observation if steps else "",
            "steps": [
                {
                    "thought": s.thought,
                    "action": s.action,
                    "observation": s.observation,
                    "drift_score": s.drift_score,
                    "drift_triggered": s.drift_triggered,
                }
                for s in steps
            ],
            "done": steps[-1].done if steps else False,
            "drift_score": self.goal_guard.drift_score if self.goal_guard else 0.0,
        }

    def _build_prompt(self, task: str, steps: list[ReActStep]) -> str:
        lines = [f"Task: {task}\n"]
        for i, step in enumerate(steps, 1):
            lines.append(f"Step {i}:")
            lines.append(f"  Thought: {step.thought}")
            lines.append(f"  Action: {step.action}({step.action_input})")
            lines.append(f"  Observation: {step.observation[:500]}")
        lines.append("\nNext step:")
        return "\n".join(lines)

    def _parse_response(self, response: str) -> dict[str, Any] | None:
        import json
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            else:
                json_str = response
            return json.loads(json_str)
        except Exception:
            return None

    async def _call_model(self, session: Any, prompt: str) -> str:
        try:
            result = await self.engine.run_agent(session, prompt)
            return result.get("output", "")
        except Exception as e:
            return f"Error: {e!s}"

    async def _execute_action(self, action: str, action_input: dict[str, Any]) -> str:
        if action in self.tools:
            try:
                from app.tools import tool_registry
                result = await tool_registry.execute(action, action_input)
                return str(result)
            except Exception as e:
                return f"Error executing {action}: {e!s}"
        return f"Unknown action: {action}"
