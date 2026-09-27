"""Solver layer for evaluation (research-100 P1).

A solver executes a task prompt and yields a normalized result the scorer can
consume. The bundled HeadlessSolver wraps the existing bounded headless runner
so solving stays deterministic and does not require a server or database.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from app.headless.model import ScriptedFakeModel
from app.headless.runner import Budget, HeadlessRunner, RunResult
from app.headless.workspace import WorkspaceSandbox

if TYPE_CHECKING:
    from .task import EvalTask


class SolverResult(Protocol):
    status: int
    output: str
    tokens: int
    turns: int
    tool_calls: int


@dataclass
class HeadlessSolver:
    """Solve eval tasks with the headless runner against a dedicated workspace.

    `fake_script` is a reusable scripted-model config that avoids a live LLM in
    tests; pass a callable `model_factory` returning an OpenAICompatibleModel
    to solve against a real endpoint.
    """

    workspace_root: Path
    fake_script: list | None = None
    model_factory: object | None = None
    max_turns: int = 20
    max_tool_calls: int = 50
    max_tokens: int = 32000
    max_seconds: float = 120

    def solve(self, task: EvalTask) -> RunResult:
        workspace_root = Path(self.workspace_root).resolve()
        workspace_root.mkdir(parents=True, exist_ok=True)
        workspace = WorkspaceSandbox(workspace_root)
        if self.fake_script is None and self.model_factory is None:
            raise ValueError("HeadlessSolver requires fake_script or model_factory")
        model = (
            ScriptedFakeModel(self.fake_script)
            if self.model_factory is None
            else self.model_factory()
        )
        budget = Budget(self.max_turns, self.max_tool_calls, self.max_tokens, self.max_seconds)
        runner = HeadlessRunner(model, workspace, budget)
        payload = {"id": task.id, "prompt": task.prompt}
        trace = StringIO()
        return runner.run(payload, trace)
