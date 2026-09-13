import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.headless.cli import main
from app.headless.model import ModelError, OpenAICompatibleModel, ScriptedFakeModel
from app.headless.runner import Budget, ExitStatus, HeadlessRunner, load_task
from app.headless.workspace import WorkspaceSandbox


def response(content="Finished", calls=None, tokens=10, finish=None):
    return {
        "usage": {"total_tokens": tokens},
        "choices": [
            {
                "finish_reason": finish or ("tool_calls" if calls else "stop"),
                "message": {"role": "assistant", "content": content, "tool_calls": calls or []},
            }
        ],
    }


def call(name="write_file", arguments=None, call_id="c1"):
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments or {"path": "hello.txt", "content": "hello"})},
    }


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work = self.root / "work"
        self.work.mkdir()
        self.workspace = WorkspaceSandbox(self.work)

    def run_script(self, script, **budget):
        trace = io.StringIO()
        result = HeadlessRunner(ScriptedFakeModel(script), self.workspace, Budget(**budget)).run(
            {"id": "test", "prompt": "Write hello"}, trace
        )
        events = [json.loads(line) for line in trace.getvalue().splitlines()]
        self.assertEqual(events[-1]["event"], "finish")
        self.assertEqual(events[-1], {**events[-1], **result.to_dict()})
        self.assertEqual(result.verification, "not_run")
        return result, events

    def test_complete_file_loop(self):
        result, events = self.run_script([response(calls=[call()]), response()])
        self.assertEqual(result.status, ExitStatus.MODEL_COMPLETED_UNVERIFIED)
        self.assertNotEqual(result.status, 0)
        self.assertEqual(result.tool_errors, 0)
        self.assertEqual((self.work / "hello.txt").read_text(), "hello")
        self.assertEqual(result.tokens, 20)
        self.assertEqual(result.tool_calls, 1)
        self.assertEqual(events[0]["model"], "scripted-fake")

    def test_text_only_completion_is_unverified(self):
        result, _ = self.run_script([response("Everything succeeded")])
        self.assertEqual(result.status, ExitStatus.MODEL_COMPLETED_UNVERIFIED)
        self.assertNotEqual(result.status, 0)
        self.assertEqual(result.tool_calls, 0)
        self.assertEqual(result.tool_errors, 0)
        self.assertIn("independent verification not performed", result.reason)

    def test_file_tool_failure_then_completion_is_unverified(self):
        for error in (ValueError, OSError, RuntimeError):
            with self.subTest(error=error), patch.object(self.workspace, "execute", side_effect=error):
                result, _ = self.run_script([response(calls=[call()]), response("Everything succeeded")])
            self.assertEqual(result.status, ExitStatus.MODEL_COMPLETED_UNVERIFIED)
            self.assertNotEqual(result.status, 0)
            self.assertEqual(result.tool_errors, 1)
            self.assertIn("1 file tool error(s) observed (rejected or failed)", result.reason)
            self.assertIn("recovery not verified", result.reason)

    def test_tool_error_allows_later_correction(self):
        result, _ = self.run_script([
            response(calls=[call("read_file", {"path": "missing.txt"})]),
            response(calls=[call()]),
            response(),
        ])
        self.assertEqual(result.status, ExitStatus.MODEL_COMPLETED_UNVERIFIED)
        self.assertEqual(result.tool_errors, 1)
        self.assertEqual(result.tool_calls, 2)
        self.assertEqual((self.work / "hello.txt").read_text(), "hello")

    def test_returned_tool_errors_are_diagnostic_on_budget_exhaustion(self):
        with patch.object(self.workspace, "execute", return_value={"error": "failed"}):
            result, _ = self.run_script([response(calls=[call(), call(call_id="c2")])], max_turns=1)
        self.assertEqual(result.status, ExitStatus.BUDGET_EXHAUSTED)
        self.assertEqual(result.tool_errors, 2)
        self.assertIn("turn budget exhausted", result.reason)
        self.assertIn("2 file tool error(s)", result.reason)

    def test_read_list_and_limits(self):
        self.workspace.execute("write_file", {"path": "nested/a", "content": "text"})
        self.assertEqual(self.workspace.execute("read_file", {"path": "nested/a"}), {"content": "text"})
        self.assertEqual(self.workspace.execute("list_files", {"path": "."}), {"entries": ["nested/"]})
        with self.assertRaises(ValueError):
            WorkspaceSandbox(self.work, 2).execute("read_file", {"path": "nested/a"})
        with self.assertRaises(ValueError):
            WorkspaceSandbox(self.work, 2).execute("write_file", {"path": "a", "content": "long"})

    def test_containment_and_protected_paths(self):
        (self.work / "outside").symlink_to(self.root, target_is_directory=True)
        for path in ("../escape", str(self.root / "absolute"), "outside/escape", ".git/config", ".env"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.workspace.execute("write_file", {"path": path, "content": "x"})

    def test_hardlink_write_rejected(self):
        original = self.root / "original"
        original.write_text("safe")
        os.link(original, self.work / "linked")
        with self.assertRaises(ValueError):
            self.workspace.execute("write_file", {"path": "linked", "content": "changed"})
        self.assertEqual(original.read_text(), "safe")

    def test_command_fail_closed(self):
        with self.assertRaises(ValueError):
            self.workspace.execute("run_command", {"command": "true"})
        result, events = self.run_script([response(calls=[call("run_command")]), response()])
        self.assertEqual(result.status, ExitStatus.MODEL_COMPLETED_UNVERIFIED)
        self.assertEqual(result.tool_errors, 1)
        self.assertFalse(next(e for e in events if e["event"] == "tool_result")["ok"])

    def test_turn_budget(self):
        result, _ = self.run_script([response(calls=[call()])], max_turns=1)
        self.assertEqual(result.status, ExitStatus.BUDGET_EXHAUSTED)

    def test_tool_budget_prevents_partial_batch(self):
        result, _ = self.run_script([response(calls=[call(), call(call_id="c2")])], max_tool_calls=1)
        self.assertEqual(result.status, ExitStatus.BUDGET_EXHAUSTED)
        self.assertFalse((self.work / "hello.txt").exists())

    def test_token_budget_prevents_tools(self):
        result, _ = self.run_script([response(calls=[call()], tokens=11)], max_tokens=10)
        self.assertEqual(result.status, ExitStatus.BUDGET_EXHAUSTED)
        self.assertFalse((self.work / "hello.txt").exists())

    def test_time_budget_prevents_request(self):
        with patch("app.headless.runner.time.monotonic", side_effect=[0, 0, 5, 5]):
            result, _ = self.run_script([], max_seconds=1)
        self.assertEqual(result.status, ExitStatus.BUDGET_EXHAUSTED)

    def test_malformed_response_and_usage_fail(self):
        for item in (
            {},
            response(tokens=-1),
            response(tokens=True),
            response(finish="length"),
            response(calls=[call(), call()]),
        ):
            with self.subTest(item=item):
                result, _ = self.run_script([item])
                self.assertEqual(result.status, ExitStatus.ERROR)

    def test_script_exhaustion(self):
        result, _ = self.run_script([])
        self.assertEqual(result.status, ExitStatus.ERROR)

    def test_budget_validation(self):
        for kwargs in (
            {"max_turns": 0},
            {"max_tokens": -1},
            {"max_seconds": float("nan")},
            {"max_seconds": float("inf")},
            {"max_tool_calls": True},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Budget(**kwargs)

    def test_task_formats(self):
        task = self.root / "task.txt"
        task.write_text("Implement greeting")
        self.assertEqual(load_task(task)["id"], "task")
        task = self.root / "task.json"
        task.write_text('{"id":"a","prompt":"hello"}')
        self.assertEqual(load_task(task)["id"], "a")
        for data in ("[]", "{}", '{"prompt":""}', '{"prompt":"x","command":"x"}'):
            task.write_text(data)
            with self.assertRaises(ValueError):
                load_task(task)

    def test_cli_fake_subprocess_and_no_server_imports(self):
        task = self.root / "task.txt"
        task.write_text("Create greeting")
        script = self.root / "fake.json"
        script.write_text(json.dumps([response(calls=[call()]), response()]))
        trace = self.root / "trace.jsonl"
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "app.headless",
                "--task",
                str(task),
                "--workspace",
                str(self.work),
                "--trace",
                str(trace),
                "--fake-model",
                str(script),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 4, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["model"], "scripted-fake")
        self.assertEqual(result["status"], 4)
        self.assertEqual(result["status_name"], "model_completed_unverified")
        self.assertEqual(result["verification"], "not_run")
        self.assertEqual(result["tool_errors"], 0)
        finish = json.loads(trace.read_text().splitlines()[-1])
        self.assertEqual({key: finish[key] for key in result}, result)
        probe = subprocess.run(
            [
                sys.executable,
                "-c",
                "import app.headless.cli,sys; "
                "assert not any(n.startswith(('fastapi','sqlalchemy','app.storage')) "
                "for n in sys.modules)",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(probe.returncode, 0, probe.stderr)

    def test_cli_rejects_trace_inside_workspace_and_existing_trace(self):
        task = self.root / "task.txt"
        task.write_text("Task")
        fake = self.root / "fake.json"
        fake.write_text("[]")
        existing = self.root / "existing.jsonl"
        existing.write_text("preserved")
        for trace in (self.work / "trace.jsonl", existing):
            with patch("sys.stderr", new=io.StringIO()):
                code = main(
                    [
                        "--task",
                        str(task),
                        "--workspace",
                        str(self.work),
                        "--trace",
                        str(trace),
                        "--fake-model",
                        str(fake),
                    ]
                )
            self.assertEqual(code, 2)
        self.assertEqual(existing.read_text(), "preserved")

    def test_http_client_payload(self):
        model = OpenAICompatibleModel("https://example.com/v1", "test-model", "test-placeholder")
        context = unittest.mock.MagicMock()
        context.__enter__.return_value.read.return_value = json.dumps(response()).encode()
        opener = unittest.mock.Mock()
        opener.open.return_value = context
        with patch("urllib.request.build_opener", return_value=opener):
            self.assertEqual(model.complete([], [], 42, 3), response())
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, "https://example.com/v1/chat/completions")
        self.assertEqual(json.loads(request.data)["max_tokens"], 42)
        self.assertEqual(opener.open.call_args.kwargs["timeout"], 3)

    def test_http_error_redaction(self):
        import urllib.error

        model = OpenAICompatibleModel("https://example.com/v1", "test", "placeholder")
        with (
            patch(
                "urllib.request.OpenerDirector.open",
                side_effect=urllib.error.HTTPError(model.url, 401, "sensitive response", {}, None),
            ),
            self.assertRaisesRegex(ModelError, "HTTP error 401"),
        ):
            model.complete([], [], 10, 1)

    def test_model_config(self):
        with (
            patch.dict(os.environ, {"USER_LLM_API_KEY": "", "USER_LLM_MODEL": ""}, clear=True),
            self.assertRaises(ValueError),
        ):
            OpenAICompatibleModel.from_environment()
        for url in ("http://example.com/v1", "file:///tmp/x", "https://user:pass@example.com/v1"):
            with self.assertRaises(ValueError):
                OpenAICompatibleModel(url, "model", "placeholder")


if __name__ == "__main__":
    unittest.main()
