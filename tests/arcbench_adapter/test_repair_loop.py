"""Acceptance repair loop: fix -> re-verify, honesty preserved, MAX=0 guard."""

import importlib.util
import json
import os
import sys
import tempfile
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

BUNDLE = Path(__file__).resolve().parents[2] / "adapters" / "arcbench"
SPEC = importlib.util.spec_from_file_location("arcbench_repair_loop_main", BUNDLE / "main.py")
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


TREE = {"id": "root", "type": "FOLDER", "children": [{"id": "REQ-1"}, {"id": "REQ-2"}]}


def acc_failed():
    return {
        "ran": True, "available": True, "passed": False, "all_specs_green": False,
        "passed_nodes": ["REQ-1"], "evidence_failed": ["REQ-2"], "unknown": [],
        "fallback": False, "specs": 2, "message": "2 spec(s) executed, 1 failing",
        "specs_detail": [
            {"file": "REQ-1.spec.ts", "titles": ["REQ-1 shows dashboard"], "passed": True},
            {"file": "REQ-2.spec.ts", "titles": ["REQ-2 checkout"], "passed": False},
        ],
    }


def acc_passed():
    return {
        "ran": True, "available": True, "passed": True, "all_specs_green": True,
        "passed_nodes": ["REQ-1", "REQ-2"], "evidence_failed": [], "unknown": [],
        "fallback": False, "specs": 2, "message": "2 spec(s) executed, 0 failing",
        "specs_detail": [
            {"file": "REQ-1.spec.ts", "titles": ["REQ-1 shows dashboard"], "passed": True},
            {"file": "REQ-2.spec.ts", "titles": ["REQ-2 checkout"], "passed": True},
        ],
    }


class _RecordingRuntime:
    def __init__(self):
        self.events = self
        self.generated = []
        self.seq = 0
        self.traceability = MagicMock()
        self.git = MagicMock()

    def _record(self, name, node_id=None, message=None):
        self.seq += 1
        self.generated.append((self.seq, name, node_id, message))

    def mark_test_passed(self, node_id, message=None):
        self._record("mark_test_passed", node_id, message)

    def mark_test_failed(self, node_id, message=None):
        self._record("mark_test_failed", node_id, message)

    def mark_run_failed(self, message=None):
        self._record("mark_run_failed", None, message)

    def mark_run_completed(self, message=None):
        self._record("mark_run_completed", None, message)


def run_flow(env_passes, acc_results, memory_env="1"):
    runtime = _RecordingRuntime()
    acceptance_calls = []
    repair_prompts = []
    acc_iter = iter(acc_results)

    def _acceptance(*args, **kwargs):
        acceptance_calls.append(kwargs)
        return next(acc_iter)

    def _turn_router(driver, prompt, ok_text, label, deadline, timeout, attempts=2, stats=None):
        if str(label).startswith("acceptance-repair-pass-"):
            repair_prompts.append((label, prompt))
            return True, "repair applied"
        return True, "VERDICT: PASS"

    out = {}
    with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
        stack.enter_context(patch.dict(sys.modules, {"agent_driver": MagicMock()}))
        stack.enter_context(patch.dict(os.environ, {
            "CLIMBER_ARC_ACCEPTANCE_REPAIR_PASSES": str(env_passes),
            "CLIMBER_ARC_ACCEPTANCE_MEMORY": memory_env,
        }))
        for name, value in {
            "load_requirement_tree": TREE,
            "tests_injection": "",
            "deliverable_ok": True,
            "run_turn": (True, "ok"),
            "rehearse_best_effort": (None, 1),
        }.items():
            stack.enter_context(patch.object(adapter, name, return_value=value))
        stack.enter_context(patch.object(adapter, "run_prompt_with_retries", side_effect=_turn_router))
        stack.enter_context(patch.object(adapter.acceptance, "run_acceptance", side_effect=_acceptance))
        stack.enter_context(patch.object(adapter, "find_spec_files", return_value=[(Path(directory), [])]))
        for name in ("PortWatchdog", "postflight_structure", "_free_web_port", "log"):
            stack.enter_context(patch.object(adapter, name))
        adapter.run(
            MagicMock(), Path(directory), Path(directory), 3000, 3100,
            100, 10, runtime, time.monotonic() + 600,
        )
        evidence_dir = Path(directory) / ".arc" / "traceability"
        evidence_files = sorted(evidence_dir.glob("acceptance-evidence*.json")) if evidence_dir.is_dir() else []
        out["evidence"] = [json.loads(p.read_text()) for p in evidence_files] if evidence_files else []
        memory_file = Path(directory) / ".arc" / "memory.json"
        out["memory"] = (json.loads(memory_file.read_text()) if memory_file.is_file() else None)
    out["runtime"] = runtime
    out["acceptance_calls"] = len(acceptance_calls)
    out["repair_prompts"] = repair_prompts
    return out


class RepairLoopTests(unittest.TestCase):
    def _passed(self, runtime):
        return [e[2] for e in runtime.generated if e[1] == "mark_test_passed"]

    def _failed(self, runtime):
        return [e[2] for e in runtime.generated if e[1] == "mark_test_failed"]

    def test_second_round_pass_emits_passed_once_and_in_order(self):
        out = run_flow(1, [acc_failed(), acc_passed()])
        self.assertEqual(out["acceptance_calls"], 2)
        self.assertEqual(len(out["repair_prompts"]), 1)
        label, prompt = out["repair_prompts"][0]
        self.assertEqual(label, "acceptance-repair-pass-1")
        self.assertIn("REQ-2", prompt)
        self.assertIn("REQ-2 checkout", prompt)
        self.assertIn("2 spec(s) executed, 1 failing", prompt)
        # honesty: REQ-2 is passed exactly once, from the second (passing) round,
        # and is never emitted as failed.
        self.assertEqual(self._passed(out["runtime"]), ["REQ-1", "REQ-2"])
        self.assertEqual(self._failed(out["runtime"]), [])
        test_events = [
            (e[1], e[2])
            for e in out["runtime"].generated
            if e[1] in ("mark_test_passed", "mark_test_failed")
        ]
        self.assertEqual(test_events, [
            ("mark_test_passed", "REQ-1"),
            ("mark_test_passed", "REQ-2"),
        ])
        completed = [e for e in out["runtime"].generated if e[1] == "mark_run_completed"]
        self.assertTrue(completed)
        self.assertIn("independent acceptance tests passed", completed[-1][3])
        # two-round success leaves nothing to remember
        self.assertIsNone(out["memory"])

    def test_second_round_still_failing_never_marks_passed(self):
        out = run_flow(1, [acc_failed(), acc_failed()])
        self.assertEqual(out["acceptance_calls"], 2)
        self.assertEqual(len(out["repair_prompts"]), 1)
        self.assertEqual(self._passed(out["runtime"]), ["REQ-1"])
        self.assertEqual(self._failed(out["runtime"]), ["REQ-2"])
        run_failed = [e for e in out["runtime"].generated if e[1] == "mark_run_failed"]
        self.assertTrue(run_failed)
        self.assertIn("failed_nodes=['REQ-2']", run_failed[-1][3])
        # still-failing node is persisted to memory for the next run
        self.assertIsNotNone(out["memory"])
        node_ids = [e["node_id"] for e in out["memory"]]
        self.assertIn("REQ-2", node_ids)
        entry = next(e for e in out["memory"] if e["node_id"] == "REQ-2")
        self.assertEqual(entry["titles"], ["REQ-2 checkout"])

    def test_repair_passes_zero_skips_loop(self):
        out = run_flow(0, [acc_failed()])
        self.assertEqual(out["acceptance_calls"], 1)
        self.assertEqual(out["repair_prompts"], [])
        self.assertEqual(self._passed(out["runtime"]), ["REQ-1"])
        self.assertEqual(self._failed(out["runtime"]), ["REQ-2"])

    def test_evidence_pack_persisted_with_sums_and_nodes(self):
        out = run_flow(1, [acc_failed(), acc_passed()])
        self.assertTrue(out["evidence"])
        pack = out["evidence"][0]
        self.assertEqual(pack["sum"]["passed"], 2)
        self.assertEqual(pack["sum"]["failed"], 0)
        self.assertEqual(pack["sum"]["unknown"], 0)
        self.assertEqual(pack["passed_nodes"], ["REQ-1", "REQ-2"])
        self.assertEqual(pack["evidence_failed"], [])
        self.assertEqual(pack["fallback"], False)
        self.assertEqual(len(pack["specs"]), 2)

    def test_memory_disabled_writes_nothing(self):
        out = run_flow(1, [acc_failed()], memory_env="0")
        self.assertIsNone(out["memory"])


if __name__ == "__main__":
    unittest.main()
