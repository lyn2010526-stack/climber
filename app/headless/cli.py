"""Independent CLI: no server, database, or third-party agent imports."""

import argparse
import json
import sys
from pathlib import Path

from .model import OpenAICompatibleModel, ScriptedFakeModel
from .runner import Budget, ExitStatus, HeadlessRunner, load_task
from .workspace import WorkspaceSandbox


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local headless coding harness (file tools only)")
    parser.add_argument("--task", required=True, help="UTF-8 text or JSON {id, prompt}")
    parser.add_argument("--workspace", required=True, help="Existing dedicated directory")
    parser.add_argument("--trace", required=True, help="New JSONL file outside workspace")
    parser.add_argument("--fake-model", help="Explicit scripted fake response JSON array")
    parser.add_argument("--max-turns", type=int, default=20)
    parser.add_argument("--max-tool-calls", type=int, default=50)
    parser.add_argument("--max-tokens", type=int, default=32000)
    parser.add_argument("--max-seconds", type=float, default=120)
    args = parser.parse_args(argv)
    try:
        task = load_task(args.task)
        workspace = WorkspaceSandbox(args.workspace)
        budget = Budget(args.max_turns, args.max_tool_calls, args.max_tokens, args.max_seconds)
        trace_path = Path(args.trace).resolve()
        if trace_path.is_relative_to(workspace.root):
            raise ValueError("Trace must be outside workspace")
        if args.fake_model:
            with Path(args.fake_model).open("rb") as stream:
                raw = stream.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError("Fake script exceeds byte limit")
            model = ScriptedFakeModel(json.loads(raw))
        else:
            model = OpenAICompatibleModel.from_environment()
        with trace_path.open("x", encoding="utf-8") as trace:
            result = HeadlessRunner(model, workspace, budget).run(task, trace)
        print(json.dumps(result.to_dict()))
        return int(result.status)
    except (OSError, ValueError, RuntimeError):
        print(
            json.dumps(
                {
                    "status": 2,
                    "status_name": "invalid_input",
                    "reason": "Check task, workspace, new trace path, budgets and USER_LLM configuration",
                }
            ),
            file=sys.stderr,
        )
        return int(ExitStatus.INVALID_INPUT)


if __name__ == "__main__":
    sys.exit(main())
