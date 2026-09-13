"""Bounded synchronous execution loop with append-only event output."""

import json
import math
import time
from dataclasses import asdict, dataclass
from enum import IntEnum
from pathlib import Path

from .model import ModelError
from .workspace import TOOLS, WorkspaceSandbox


class ExitStatus(IntEnum):
    # Reserved for a future independent acceptance check.
    SUCCESS = 0
    ERROR = 1
    INVALID_INPUT = 2
    BUDGET_EXHAUSTED = 3
    MODEL_COMPLETED_UNVERIFIED = 4


@dataclass
class Budget:
    max_turns: int = 20
    max_tool_calls: int = 50
    max_tokens: int = 32000
    max_seconds: float = 120

    def __post_init__(self):
        for value in (self.max_turns, self.max_tool_calls, self.max_tokens):
            if type(value) is not int or value <= 0:
                raise ValueError("Count budgets must be positive integers")
        if not math.isfinite(self.max_seconds) or self.max_seconds <= 0:
            raise ValueError("Time budget must be finite and positive")


@dataclass
class RunResult:
    status: ExitStatus
    task_id: str
    model: str
    turns: int = 0
    tool_calls: int = 0
    tokens: int = 0
    output: str = ""
    reason: str = ""
    verification: str = "not_run"
    tool_errors: int = 0

    def to_dict(self):
        return {**asdict(self), "status": int(self.status), "status_name": self.status.name.lower()}


def load_task(path: str | Path) -> dict:
    path = Path(path)
    with path.open("rb") as stream:
        raw = stream.read(262145)
    if len(raw) > 262144:
        raise ValueError("Task exceeds byte limit")
    text = raw.decode("utf-8")
    task = json.loads(text) if path.suffix.lower() == ".json" else {"prompt": text}
    if not isinstance(task, dict) or set(task) - {"id", "prompt"}:
        raise ValueError("Task must contain prompt and optional id only")
    if not isinstance(task.get("prompt"), str) or not task["prompt"].strip():
        raise ValueError("Task prompt must be nonempty text")
    task.setdefault("id", path.stem)
    if not isinstance(task["id"], str) or not task["id"].strip():
        raise ValueError("Task id must be nonempty text")
    return task


class HeadlessRunner:
    def __init__(self, model, workspace: WorkspaceSandbox, budget: Budget | None = None):
        self.model = model
        self.workspace = workspace
        self.budget = budget or Budget()

    def run(self, task: dict, trace, system_prompt: str | None = None) -> RunResult:
        budget = self.budget
        result = RunResult(ExitStatus.ERROR, task["id"], self.model.label)
        started = time.monotonic()
        tools = getattr(self.workspace, "tools", TOOLS)

        def emit(event, **fields):
            trace.write(
                json.dumps({"event": event, "elapsed_seconds": time.monotonic() - started, **fields}, ensure_ascii=True)
                + "\n"
            )
            trace.flush()

        def exhausted(reason):
            result.status = ExitStatus.BUDGET_EXHAUSTED
            result.reason = reason

        messages = [
            {
                "role": "system",
                "content": system_prompt
                or (
                    "Implement the task using the available file tools. Paths are workspace-relative. "
                    "Command execution is disabled. Give a final text summary when finished. "
                    "Clearly state any tests you could not run. Never claim unperformed verification."
                ),
            },
            {"role": "user", "content": task["prompt"]},
        ]
        emit("start", task_id=task["id"], model=self.model.label, budget=asdict(budget))
        try:
            for _ in range(budget.max_turns):
                remaining = budget.max_seconds - (time.monotonic() - started)
                if remaining <= 0 or result.tokens >= budget.max_tokens:
                    exhausted("time or token budget exhausted")
                    break
                result.turns += 1
                emit("model_request", turn=result.turns)
                response = self.model.complete(messages, TOOLS, min(4096, budget.max_tokens - result.tokens), remaining)
                usage = response.get("usage", {}).get("total_tokens")
                if type(usage) is not int or usage < 0:
                    raise ModelError("Model response requires nonnegative usage.total_tokens")
                result.tokens += usage
                emit("model_usage", turn=result.turns, tokens=usage)
                if time.monotonic() - started >= budget.max_seconds or result.tokens > budget.max_tokens:
                    exhausted("time or token budget exceeded by response")
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
                    result.reason = "model completed; independent verification not performed"
                    break
                if choice.get("finish_reason") != "tool_calls":
                    raise ModelError("Incomplete tool call response")
                if result.tool_calls + len(calls) > budget.max_tool_calls:
                    exhausted("tool call budget exhausted")
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
                messages.append({"role": "assistant", "content": content, "tool_calls": calls})
                for call_id, name, arguments in parsed:
                    if time.monotonic() - started >= budget.max_seconds:
                        exhausted("time budget exhausted before tool")
                        break
                    result.tool_calls += 1
                    emit("tool_start", call_id=call_id, name=name)
                    try:
                        output = self.workspace.execute(name, arguments)
                    except (ValueError, OSError, RuntimeError) as exc:
                        output = {"error": type(exc).__name__, "message": "File tool rejected or failed"}
                    if "error" in output:
                        result.tool_errors += 1
                    emit("tool_result", call_id=call_id, name=name, ok="error" not in output)
                    messages.append({"role": "tool", "tool_call_id": call_id, "content": json.dumps(output)})
                if result.status == ExitStatus.BUDGET_EXHAUSTED:
                    break
            else:
                exhausted("turn budget exhausted")
        except (ModelError, KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
            result.reason = str(exc) if isinstance(exc, ModelError) else "Malformed model response"
        if result.tool_errors:
            result.reason += (
                f"; {result.tool_errors} file tool error(s) observed (rejected or failed); recovery not verified"
            )
        emit("finish", **result.to_dict())
        return result
