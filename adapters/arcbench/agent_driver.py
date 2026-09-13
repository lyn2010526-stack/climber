"""Driver that maps ARC-Bench agent turns onto the repo's app/headless harness.

Every model turn goes through :class:`AgentSession`, which reuses
``app.headless`` components (``OpenAICompatibleModel``, ``WorkspaceSandbox``
with the backward-compatible ``run_command`` extension, ``Budget`` and
``ExitStatus`` semantics from ``HeadlessRunner``) while keeping the message
history at driver level. A session chains messages across turns of the same
node so context is reused; a new session starts from an empty history, which
is how cross-attempt session resets are implemented.
"""

import io
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.headless.model import ModelError, OpenAICompatibleModel, ScriptedFakeModel  # noqa: E402
from app.headless.runner import Budget, ExitStatus, RunResult  # noqa: E402
from app.headless.workspace import WorkspaceSandbox  # noqa: E402

SYSTEM_PROMPT = (
    "You are building a complete web application inside the workspace (the graded output "
    "directory). Paths are workspace-relative. Write real files first; never describe work "
    "instead of doing it. Use run_command for builds and self-tests (npm install, npm run "
    "build, starting servers for smoke tests), but NEVER bind the grading port - use the "
    "smoke port injected in the environment (PORT) for any server you start. Give a final "
    "text summary when finished. Never claim verification you did not perform."
)


class AgentSession:
    """One conversation chain against one workspace sandbox."""

    def __init__(
        self,
        model,
        workspace: WorkspaceSandbox,
        budget: Budget,
        trace=None,
    ):
        self.model = model
        self.workspace = workspace
        self.budget = budget
        self.messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        self.trace = trace if trace is not None else io.StringIO()
        self.result_turns = 0
        self.result_tool_calls = 0
        self.result_tokens = 0
        self.tool_errors = 0
        self.last_text = ""

    @property
    def spawned_pgids(self) -> set[int]:
        return self.workspace.spawned_pgids

    def run_turn(self, prompt: str, wall_deadline: float | None = None) -> tuple[bool, str]:
        """One user turn: model -> tools -> ... until final text or budget/model failure.

        Returns (ok, last_text). ok means the assistant produced a final
        answer; failures (transport, budget, malformed response) yield ok=False.
        """

        budget = self.budget
        result = RunResult(ExitStatus.ERROR, "arc-turn", self.model.label)
        started = time.monotonic()
        self.messages.append({"role": "user", "content": prompt})

        def emit(event, **fields):
            self.trace.write(
                json.dumps({"event": event, "elapsed_seconds": time.monotonic() - started, **fields}) + "\n"
            )
            self.trace.flush()

        def time_left() -> float:
            remaining = budget.max_seconds - (time.monotonic() - started)
            if wall_deadline is not None:
                remaining = min(remaining, wall_deadline - time.monotonic())
            return remaining

        emit("start", model=self.model.label, budget=asdict(budget))
        try:
            for _ in range(budget.max_turns):
                if time_left() <= 0 or result.tokens >= budget.max_tokens:
                    result.status = ExitStatus.BUDGET_EXHAUSTED
                    result.reason = "time or token budget exhausted"
                    break
                result.turns += 1
                emit("model_request", turn=result.turns)
                response = self.model.complete(
                    self.messages,
                    self.workspace.tools,
                    min(4096, budget.max_tokens - result.tokens),
                    max(5.0, time_left()),
                )
                usage = response.get("usage", {}).get("total_tokens")
                if type(usage) is not int or usage < 0:
                    raise ModelError("Model response requires nonnegative usage.total_tokens")
                result.tokens += usage
                if time_left() <= 0 or result.tokens > budget.max_tokens:
                    result.status = ExitStatus.BUDGET_EXHAUSTED
                    result.reason = "time or token budget exceeded by response"
                    break
                choice = response["choices"][0]
                message = choice["message"]
                if message.get("role") != "assistant":
                    raise ModelError("Expected assistant message")
                calls = message.get("tool_calls") or []
                content = message.get("content")
                if not isinstance(calls, list) or (content is not None and not isinstance(content, str)):
                    raise ModelError("Invalid assistant message")
                if not calls:
                    if choice.get("finish_reason") != "stop" or not content or not content.strip():
                        raise ModelError("Expected complete, nonempty final answer")
                    result.status = ExitStatus.MODEL_COMPLETED_UNVERIFIED
                    result.output = content
                    self.messages.append({"role": "assistant", "content": content})
                    result.reason = "model completed; independent verification not performed"
                    break
                if choice.get("finish_reason") != "tool_calls":
                    raise ModelError("Incomplete tool call response")
                if result.tool_calls + len(calls) > budget.max_tool_calls:
                    result.status = ExitStatus.BUDGET_EXHAUSTED
                    result.reason = "tool call budget exhausted"
                    break
                ids = set()
                parsed = []
                for call in calls:
                    call_id = call["id"]
                    if not isinstance(call_id, str) or not call_id or call_id in ids or call.get("type") != "function":
                        raise ModelError("Invalid or duplicate tool call id")
                    ids.add(call_id)
                    function = call["function"]
                    arguments = json.loads(function["arguments"])
                    if not isinstance(arguments, dict) or not isinstance(function["name"], str):
                        raise ModelError("Invalid tool arguments")
                    parsed.append((call_id, function["name"], arguments))
                self.messages.append({"role": "assistant", "content": content, "tool_calls": calls})
                for call_id, name, arguments in parsed:
                    if time_left() <= 0:
                        result.status = ExitStatus.BUDGET_EXHAUSTED
                        result.reason = "time budget exhausted before tool"
                        break
                    result.tool_calls += 1
                    emit("tool_start", call_id=call_id, name=name)
                    try:
                        output = self.workspace.execute(name, arguments)
                    except (ValueError, OSError, RuntimeError) as exc:
                        message = "Command failed or rejected" if name == "run_command" else "File tool rejected or failed"
                        output = {"error": type(exc).__name__, "message": message}
                    if "error" in output:
                        result.tool_errors += 1
                    emit("tool_result", call_id=call_id, name=name, ok="error" not in output)
                    self.messages.append({"role": "tool", "tool_call_id": call_id, "content": json.dumps(output)})
                if result.status == ExitStatus.BUDGET_EXHAUSTED:
                    break
            else:
                result.status = ExitStatus.BUDGET_EXHAUSTED
                result.reason = "turn budget exhausted"
        except (ModelError, KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
            result.reason = str(exc) if isinstance(exc, ModelError) else "Malformed model response"
        self.result_turns += result.turns
        self.result_tool_calls += result.tool_calls
        self.result_tokens += result.tokens
        self.tool_errors += result.tool_errors
        self.last_text = result.output or result.reason
        ok = result.status == ExitStatus.MODEL_COMPLETED_UNVERIFIED
        emit("finish", **result.to_dict())
        return ok, self.last_text


class AgentDriver:
    """Creates ARC-env models, workspaces and sessions for one output directory."""

    def __init__(
        self,
        output_dir: Path,
        command_env: dict[str, str] | None = None,
        model=None,
        budget: Budget | None = None,
        trace=None,
        command_timeout: float = 180.0,
    ):
        self.output_dir = Path(output_dir)
        self.command_env = dict(command_env or {})
        self._model = model
        self.budget = budget or Budget(max_turns=25, max_tool_calls=120, max_tokens=200_000, max_seconds=900)
        self.command_timeout = command_timeout
        self.trace = trace if trace is not None else io.StringIO()
        self._workspaces: list[WorkspaceSandbox] = []
        if model is None:
            self._model = OpenAICompatibleModel.from_arc_env()

    @property
    def model(self):
        return self._model

    @staticmethod
    def make_model_from_env() -> OpenAICompatibleModel:
        return OpenAICompatibleModel.from_arc_env()

    @staticmethod
    def fake_model(responses: list) -> ScriptedFakeModel:
        return ScriptedFakeModel(responses)

    def new_sandbox(self) -> WorkspaceSandbox:
        workspace = WorkspaceSandbox(
            self.output_dir,
            allow_commands=True,
            command_timeout=self.command_timeout,
            command_env=self.command_env,
        )
        self._workspaces.append(workspace)
        return workspace

    def new_session(self, sandbox: WorkspaceSandbox | None = None) -> AgentSession:
        return AgentSession(self._model, sandbox or self.new_sandbox(), self.budget, trace=self.trace)

    @property
    def spawned_pgids(self) -> set[int]:
        """Union of process groups spawned by every sandbox this driver created."""

        pgids: set[int] = set()
        for workspace in self._workspaces:
            pgids |= workspace.spawned_pgids
        return pgids


__all__ = ["AgentDriver", "AgentSession", "SYSTEM_PROMPT"]
