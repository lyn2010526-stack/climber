"""How run() consumes acceptance results: event semantics, never fake passes."""

import importlib.util
import sys
import tempfile
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

BUNDLE = Path(__file__).resolve().parents[2] / "adapters" / "arcbench"
SPEC = importlib.util.spec_from_file_location("arcbench_acceptance_flow_main", BUNDLE / "main.py")
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


TREE = {"id": "root", "type": "FOLDER", "children": [{"id": "REQ-1"}, {"id": "REQ-2"}]}


def run_flow(acc_result):
    runtime = MagicMock()
    seen = {"passed": [], "failed": []}

    runtime.events.mark_test_passed = lambda node_id, message=None: seen["passed"].append(node_id)
    runtime.events.mark_test_failed = lambda node_id, message=None: seen["failed"].append(node_id)
    with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
        stack.enter_context(patch.dict(sys.modules, {"agent_driver": MagicMock()}))
        for name, value in {
            "load_requirement_tree": TREE,
            "tests_injection": "",
            "deliverable_ok": True,
            "run_turn": (True, "ok"),
            "run_prompt_with_retries": (True, "VERDICT: PASS"),
            "rehearse_best_effort": (None, 1),
        }.items():
            stack.enter_context(patch.object(adapter, name, return_value=value))
        if acc_result is None:
            stack.enter_context(patch.object(
                adapter.acceptance, "run_acceptance", side_effect=RuntimeError("boom")))
        else:
            stack.enter_context(patch.object(
                adapter.acceptance, "run_acceptance", return_value=acc_result))
        stack.enter_context(patch.object(adapter, "find_spec_files", return_value=[(Path(directory), [])]))
        for name in ("PortWatchdog", "postflight_structure", "_free_web_port", "log"):
            stack.enter_context(patch.object(adapter, name))
        adapter.run(
            MagicMock(), Path(directory), Path(directory), 3000, 3100,
            100, 10, runtime, time.monotonic() + 100,
        )
    return runtime, seen


class AcceptanceFlowTests(unittest.TestCase):
    def test_verified_nodes_emit_passed_events_and_honest_completion(self):
        runtime, seen = run_flow({
            "ran": True, "available": True, "passed": True, "all_specs_green": True,
            "passed_nodes": ["REQ-1", "REQ-2"], "evidence_failed": [], "unknown": [],
            "fallback": False, "specs": 2, "message": "2 spec(s) executed, 0 failing",
        })
        self.assertEqual(seen["passed"], ["REQ-1", "REQ-2"])
        self.assertEqual(seen["failed"], [])
        msg = runtime.events.mark_run_completed.call_args[0][0]
        self.assertIn("independent acceptance tests passed", msg)
        runtime.events.mark_run_failed.assert_not_called()

    def test_evidence_failure_marks_test_failed_and_run_failed(self):
        runtime, seen = run_flow({
            "ran": True, "available": True, "passed": False, "all_specs_green": False,
            "passed_nodes": ["REQ-1"], "evidence_failed": ["REQ-2"], "unknown": [],
            "fallback": False, "specs": 2, "message": "2 spec(s) executed, 1 failing",
        })
        self.assertEqual(seen["passed"], ["REQ-1"])
        self.assertEqual(seen["failed"], ["REQ-2"])
        runtime.events.mark_run_failed.assert_called_once()
        self.assertIn("failed_nodes=['REQ-2']", runtime.events.mark_run_failed.call_args[0][0])

    def test_unverified_nodes_reported_not_marked_passed(self):
        runtime, seen = run_flow({
            "ran": True, "available": True, "passed": False, "all_specs_green": True,
            "passed_nodes": ["REQ-1"], "evidence_failed": [], "unknown": ["REQ-2"],
            "fallback": False, "specs": 1,
            "message": "1 spec(s) executed, 0 failing; unverified nodes: ['REQ-2']",
        })
        self.assertEqual(seen["passed"], ["REQ-1"])
        self.assertEqual(seen["failed"], [])
        completed_msg = runtime.events.mark_run_completed.call_args[0][0]
        self.assertIn("all acceptance specs green with unverified nodes", completed_msg)

    def test_infra_unavailable_stays_honest_not_a_pass(self):
        runtime, seen = run_flow({
            "ran": False, "available": False, "passed": None, "all_specs_green": False,
            "passed_nodes": [], "evidence_failed": [], "unknown": ["REQ-1", "REQ-2"],
            "fallback": False, "specs": 0, "message": "no official spec files",
        })
        self.assertEqual(seen["passed"], [])
        self.assertEqual(seen["failed"], [])
        msg = runtime.events.mark_run_completed.call_args[0][0]
        self.assertIn("acceptance infra unavailable", msg)

    def test_runner_crash_never_marks_test_passed(self):
        runtime, seen = run_flow(None)
        self.assertEqual(seen["passed"], [])
        msg = runtime.events.mark_run_completed.call_args[0][0]
        self.assertIn("acceptance tests not run", msg)


if __name__ == "__main__":
    unittest.main()
