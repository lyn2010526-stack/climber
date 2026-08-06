"""Multi-agent orchestration engine.

Provides lightweight orchestration modes (sequential, parallel, hierarchical,
debate) over a list of agent specs. Agents are simulated via async mocks so
the module can be exercised without external model calls.
"""

from __future__ import annotations

import asyncio
import enum
from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class OrchestratorMode(str, enum.Enum):
    """Execution mode for an orchestration task."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"
    DEBATE = "debate"


class AgentSpec(BaseModel):
    """Description of a single agent participating in orchestration."""

    name: str
    role: str
    model: str
    system_prompt: str = ""
    tools: list[str] = Field(default_factory=list)


class OrchestrationTask(BaseModel):
    """A unit of work to be executed by a collection of agents."""

    id: str
    name: str
    mode: OrchestratorMode = OrchestratorMode.SEQUENTIAL
    agents: list[AgentSpec] = Field(default_factory=list)
    input: str = ""
    result: dict[str, Any] | None = None
    status: str = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentOrchestrator:
    """Orchestrates agents across multiple collaboration modes."""

    def __init__(self) -> None:
        self._history: dict[str, OrchestrationTask] = {}

    @staticmethod
    def _mock_agent(role: str, text: str) -> str:
        """Produce a role-specific mocked agent output."""
        prefixes = {
            "analyst": "[分析]",
            "writer": "[草稿]",
            "reviewer": "[评审]",
            "planner": "[计划]",
        }
        prefix = prefixes.get(role, "[输出]")
        return f"{prefix}{text}"

    async def _run_agent(self, agent: AgentSpec, text: str) -> str:
        """Simulate a single agent turn asynchronously."""
        await asyncio.sleep(0)
        return self._mock_agent(agent.role, text)

    async def run_sequential(self, task: OrchestrationTask) -> dict[str, Any]:
        """Execute agents in order, chaining each output as the next input."""
        if not task.agents:
            return {"mode": task.mode.value, "output": task.input, "steps": []}
        current = task.input
        steps: list[dict[str, str]] = []
        for agent in task.agents:
            output = await self._run_agent(agent, current)
            steps.append({"agent": agent.name, "output": output})
            current = output
        return {"mode": task.mode.value, "output": current, "steps": steps}

    async def run_parallel(self, task: OrchestrationTask) -> dict[str, Any]:
        """Execute all agents concurrently, collecting their outputs."""
        if not task.agents:
            return {"mode": task.mode.value, "results": []}
        results = await asyncio.gather(
            *(self._run_agent(agent, task.input) for agent in task.agents)
        )
        return {
            "mode": task.mode.value,
            "results": [
                {"agent": agent.name, "output": output}
                for agent, output in zip(task.agents, results, strict=True)
            ],
        }

    async def run_hierarchical(self, task: OrchestrationTask) -> dict[str, Any]:
        """Let the first agent plan, others execute, last one summarize."""
        if not task.agents:
            return {"mode": task.mode.value, "output": task.input, "plan": "", "steps": []}
        planner = task.agents[0]
        plan = await self._run_agent(planner, task.input)
        steps: list[dict[str, str]] = [{"agent": planner.name, "role": "planner", "output": plan}]
        current = plan
        workers = task.agents[1:]
        for index, agent in enumerate(workers):
            output = await self._run_agent(agent, current)
            role = "summary" if index == len(workers) - 1 else "worker"
            steps.append({"agent": agent.name, "role": role, "output": output})
            current = output
        return {"mode": task.mode.value, "plan": plan, "output": current, "steps": steps}

    async def run_debate(self, task: OrchestrationTask) -> dict[str, Any]:
        """Let two agents exchange opposing views, collecting arguments."""
        if len(task.agents) < 2:
            return {"mode": task.mode.value, "arguments": [], "conclusion": ""}
        first, second = task.agents[0], task.agents[1]
        rounds = max(1, len(task.agents) // 2)
        arguments: list[dict[str, str]] = []
        stance = task.input
        for _ in range(rounds):
            for agent, side in ((first, "for"), (second, "against")):
                stance = await self._run_agent(agent, stance)
                arguments.append({"agent": agent.name, "side": side, "argument": stance})
        return {
            "mode": task.mode.value,
            "arguments": arguments,
            "conclusion": stance,
        }

    async def execute(self, task: OrchestrationTask) -> dict[str, Any]:
        """Dispatch a task to the handler matching its mode."""
        handlers: dict[OrchestratorMode, Any] = {
            OrchestratorMode.SEQUENTIAL: self.run_sequential,
            OrchestratorMode.PARALLEL: self.run_parallel,
            OrchestratorMode.HIERARCHICAL: self.run_hierarchical,
            OrchestratorMode.DEBATE: self.run_debate,
        }
        task.status = "running"
        try:
            handler = handlers[task.mode]
            result = await handler(task)
        except Exception as e:
            logger.error("orchestration_failed", task_id=task.id, mode=task.mode.value, error=str(e))
            task.status = "failed"
            task.result = {"mode": task.mode.value, "error": str(e)}
            raise
        task.status = "completed"
        task.result = result
        self._history[task.id] = task
        logger.info("orchestration_completed", task_id=task.id, mode=task.mode.value)
        return result

    async def list_tasks(self) -> list[OrchestrationTask]:
        """Return the historical orchestration tasks."""
        return list(self._history.values())


_orchestrator: AgentOrchestrator | None = None


async def get_orchestrator() -> AgentOrchestrator:
    """Return the shared AgentOrchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator
