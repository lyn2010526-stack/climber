"""Outcome checks without models, subprocesses, git writes or network access."""

import importlib.util
import sys
import tempfile
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

BUNDLE = Path(__file__).resolve().parents[2] / "adapters" / "arcbench"
SPEC = importlib.util.spec_from_file_location("arcbench_outcomes_main", BUNDLE / "main.py")
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


class RehearsalTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "frontend").mkdir()
        (self.root / "frontend" / "package.json").write_text("{}")
        (self.root / "backend").mkdir()
        (self.root / "backend" / "package.json").write_text("{}")

    def test_install_failure_is_fatal_even_with_stale_node_modules(self):
        (self.root / "frontend" / "node_modules").mkdir()
        with patch.object(adapter, "_npm", return_value=(1, "registry unreachable")), \
                patch.object(adapter.subprocess, "Popen") as popen:
            self.assertIn("frontend npm install failed", adapter._rehearse_once(self.root, 3100))
            popen.assert_not_called()

    def test_backend_install_failure_is_fatal(self):
        with patch.object(adapter, "_npm", side_effect=[(0, ""), (0, ""), (1, "install failed")]), \
                patch.object(adapter.subprocess, "Popen") as popen:
            self.assertIn("backend npm install failed", adapter._rehearse_once(self.root, 3100))
            popen.assert_not_called()

    def test_backend_startup_is_not_killed_by_pre_bind_cleanup(self):
        calls: list[str] = []
        proc = MagicMock()
        proc.pid = 24680
        proc.poll.return_value = None
        proc.returncode = None
        with ExitStack() as stack:
            stack.enter_context(patch.object(adapter, "_npm", return_value=(0, "")))
            stack.enter_context(patch.object(adapter, "_free_web_port",
                                             side_effect=lambda port: calls.append("bind")))
            stack.enter_context(patch.object(adapter.subprocess, "Popen",
                                             side_effect=lambda *a, **k: calls.append("spawn") or proc))
            stack.enter_context(patch.object(adapter.socket, "create_connection"))
            stack.enter_context(patch.object(adapter.os, "killpg",
                                             side_effect=lambda pid, sig: calls.append("killpg")))
            self.assertIsNone(adapter._rehearse_once(self.root, 3100))
            self.assertEqual(calls[0], "bind")
            self.assertEqual(calls[1], "spawn")
            self.assertEqual(calls[-2:], ["killpg", "bind"])


class OutcomeTests(unittest.TestCase):
    def run_flow(self, *, node_ok=True, rehearsal_error=None, expired=False, empty=False):
        runtime = MagicMock()
        driver_module = MagicMock()
        tree = {"id": "root", "type": "FOLDER", "children": [] if empty else [{"id": "REQ-1"}]}
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            stack.enter_context(patch.dict(sys.modules, {"agent_driver": driver_module}))
            for name, value in {
                "load_requirement_tree": tree,
                "find_spec_files": [],
                "tests_injection": "",
                "deliverable_ok": True,
                "run_turn": (node_ok, "model reply"),
                "run_prompt_with_retries": (True, "VERDICT: PASS"),
                "rehearse_best_effort": (rehearsal_error, 1),
            }.items():
                stack.enter_context(patch.object(adapter, name, return_value=value))
            for name in ("PortWatchdog", "postflight_structure", "_free_web_port", "log"):
                stack.enter_context(patch.object(adapter, name))
            preview = stack.enter_context(patch.object(adapter, "finalize_preview"))
            result = adapter.run(
                SimpleNamespace(), Path(directory), Path(directory), 3000, 3100,
                100, 10, runtime, time.monotonic() + (-1 if expired else 100),
            )
        self.assertEqual(result, 0)
        runtime.events.mark_test_passed.assert_not_called()
        return runtime, preview

    def test_model_pass_is_unverified(self):
        runtime, preview = self.run_flow()
        runtime.events.mark_run_completed.assert_called_once()
        self.assertIn("acceptance tests not run", runtime.events.mark_run_completed.call_args.args[0])
        self.assertTrue(preview.call_args.kwargs["ready"])

    def test_rehearsal_failure_cannot_complete_or_enable_preview(self):
        runtime, preview = self.run_flow(rehearsal_error="build failed")
        runtime.events.mark_run_failed.assert_called_once()
        runtime.events.mark_run_completed.assert_not_called()
        self.assertFalse(preview.call_args.kwargs["ready"])

    def test_failed_node_with_existing_directories_stays_failed(self):
        runtime, _ = self.run_flow(node_ok=False)
        runtime.events.mark_implementation_done.assert_not_called()
        runtime.events.mark_implementation_failed.assert_called_once()
        runtime.events.mark_run_completed.assert_not_called()

    def test_expired_budget_records_skipped_nodes(self):
        runtime, _ = self.run_flow(expired=True)
        runtime.events.mark_implementation_failed.assert_called_once_with("REQ-1", "time budget exhausted")
        runtime.events.mark_run_completed.assert_not_called()

    def test_empty_requirement_tree_fails_before_driver_creation(self):
        runtime, preview = self.run_flow(empty=True)
        runtime.events.mark_run_failed.assert_called_once_with("no atomic requirement nodes found")
        runtime.events.mark_run_completed.assert_not_called()
        preview.assert_not_called()


if __name__ == "__main__":
    unittest.main()
