"""Independent GUI acceptance runner: mapping, conservative semantics, fallbacks."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

BUNDLE = Path(__file__).resolve().parents[2] / "adapters" / "arcbench"
SPEC = importlib.util.spec_from_file_location("arcbench_acceptance", BUNDLE / "acceptance.py")
acc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(acc)


def _report(suites, ok=None):
    payload = {"suites": suites}
    if ok is not None:
        payload["stats"] = {"expected": ok}
    return payload


class ReportTests(unittest.TestCase):
    def test_parses_nested_suites_and_titles(self):
        raw = _report([
            {
                "file": "req-7.spec.ts",
                "title": "req-7.spec.ts",
                "suites": [{
                    "title": "login flow",
                    "specs": [{
                        "title": "REQ-7 shows dashboard",
                        "ok": True,
                        "tests": [{"results": [{"status": "passed"}]}],
                    }],
                }],
            },
            {
                "file": "req-9.spec.ts",
                "title": "req-9.spec.ts",
                "specs": [{
                    "title": "REQ-9 checkout",
                    "ok": False,
                    "tests": [{"results": [{"status": "failed"}]}],
                }],
            },
        ])
        parsed = acc.parse_playwright_report(raw)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["file"], "req-7.spec.ts")
        self.assertEqual(parsed[0]["titles"], ["login flow", "REQ-7 shows dashboard"])
        self.assertTrue(parsed[0]["passed"])
        self.assertFalse(parsed[1]["passed"])

    def test_derives_failures_from_status_when_ok_missing(self):
        raw = _report([{
            "file": "a.spec.ts",
            "title": "a.spec.ts",
            "specs": [{
                "title": "REQ-1 works",
                "tests": [{"results": [{"status": "passed"}, {"status": "timedOut"}]}],
            }],
        }])
        parsed = acc.parse_playwright_report(raw)
        self.assertFalse(parsed[0]["passed"])

    def test_maps_node_ids_and_requires_both_specs_when_repeated(self):
        results = [
            {"file": "REQ-1.spec.ts", "titles": ["first"], "passed": True},
            {"file": "REQ-1.spec.ts", "titles": ["second"], "passed": False},
            {"file": "other.spec.ts", "titles": ["REQ-2 login"], "passed": True},
        ]
        mapped = acc.map_results_to_nodes(results, ["REQ-1", "REQ-2", "REQ-3"])
        self.assertFalse(mapped["REQ-1"])
        self.assertTrue(mapped["REQ-2"])
        self.assertNotIn("REQ-3", mapped)

    def test_try_json_from_text_embedded(self):
        text = "prefix noise " + json.dumps({"suites": [{"file": "x.spec.ts", "specs": []}]}) + " suffix"
        payload = acc.try_json_from_text(text)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["suites"][0]["file"], "x.spec.ts")

    def test_try_json_from_text_rejects_garbage(self):
        self.assertIsNone(acc.try_json_from_text("no json here"))


class _Proc:
    pid = 999999

    def __init__(self, alive=True, code=None):
        self.poll_value = None if alive else code
        self.returncode = code
        self.stdout = SimpleNamespace(read=lambda: "")
        self._waited = False

    def poll(self):
        return self.poll_value

    def wait(self, timeout=10):
        self._waited = True


class InfraTests(unittest.TestCase):
    def test_no_specs_is_inconclusive_not_failed(self):
        with tempfile.TemporaryDirectory() as dir_name:
            root = Path(dir_name)
            tests = root / "tests"
            tests.mkdir()
            summary = acc.run_acceptance(
                root, tests,
                web_port=3000, extra_ports=[], node_ids=["REQ-1"],
                free_port=lambda port: None, log=lambda m: None,
                tail=lambda t, n=999: t[-n:], deadline=None,
            )
        self.assertFalse(summary["available"])
        self.assertTrue(summary["ran"] is False)
        self.assertIsNone(summary["passed"])
        self.assertEqual(summary["unknown"], ["REQ-1"])

    def _write_deliverable(self, root: Path):
        backend = root / "backend"
        backend.mkdir()
        (backend / "package.json").write_text('{"scripts":{"start":"node server.js"}}')
        tests = root / "tests"
        tests.mkdir()
        (tests / "REQ-1.spec.ts").write_text("test('REQ-1')")
        return tests

    def test_backend_bind_failure_fails_nodes(self):
        with tempfile.TemporaryDirectory() as dir_name:
            root = Path(dir_name)
            tests = self._write_deliverable(root)
            proc = _Proc(alive=True)
            with patch.object(acc.subprocess, "Popen", return_value=proc), \
                    patch.object(acc, "wait_bound", return_value=False):
                summary = acc.run_acceptance(
                    root, tests,
                    web_port=3000, extra_ports=[8080], node_ids=["REQ-1"],
                    free_port=lambda port: None, log=lambda m: None,
                    tail=lambda t, n=999: t[-n:], deadline=float("inf"),
                )
        self.assertTrue(summary["ran"])
        self.assertFalse(summary["passed"])
        self.assertEqual(summary["evidence_failed"], ["REQ-1"])
        self.assertIn("failed to bind grading port", summary["message"])

    def test_all_specs_green_marks_every_known_node_with_fallback(self):
        with tempfile.TemporaryDirectory() as dir_name:
            root = Path(dir_name)
            tests = self._write_deliverable(root)
            report_file = Path(tempfile.mkdtemp(prefix="rep-")) / "report.json"

            def fake_run(argv, **kwargs):
                report_file.write_text(json.dumps(_report([{
                    "file": "REQ-1.spec.ts", "title": "REQ-1.spec.ts",
                    "specs": [{"title": "REQ-1 works", "ok": True}],
                }])))
                # the output path env var carries the real location
                kwargs["env"]["PLAYWRIGHT_JSON_OUTPUT_NAME"]
                Path(kwargs["env"]["PLAYWRIGHT_JSON_OUTPUT_NAME"]).write_text(
                    report_file.read_text()
                )
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            with patch.object(acc, "wait_bound", return_value=True), \
                    patch.object(acc.subprocess, "Popen", return_value=_Proc()), \
                    patch.object(acc.subprocess, "run", side_effect=fake_run), \
                    patch.object(acc, "playwright_argv", return_value=["playwright"]), \
                    patch.object(acc, "prepare_test_harness", return_value=None):
                summary = acc.run_acceptance(
                    root, tests,
                    web_port=3000, extra_ports=[], node_ids=["REQ-1"],
                    free_port=lambda port: None, log=lambda m: None,
                    tail=lambda t, n=999: t[-n:], deadline=float("inf"),
                )
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["passed_nodes"], ["REQ-1"])
        self.assertEqual(summary["unknown"], [])

    def test_unknown_nodes_cannot_pass_but_keep_node_events_fresh(self):
        with tempfile.TemporaryDirectory() as dir_name:
            root = Path(dir_name)
            tests = self._write_deliverable(root)

            def fake_run(argv, **kwargs):
                payload = _report([{
                    "file": "REQ-1.spec.ts", "title": "REQ-1.spec.ts",
                    "specs": [{"title": "REQ-1 works", "ok": True}],
                }])
                Path(kwargs["env"]["PLAYWRIGHT_JSON_OUTPUT_NAME"]).write_text(
                    json.dumps(payload)
                )
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            with patch.object(acc, "wait_bound", return_value=True), \
                    patch.object(acc.subprocess, "Popen", return_value=_Proc()), \
                    patch.object(acc.subprocess, "run", side_effect=fake_run), \
                    patch.object(acc, "playwright_argv", return_value=["playwright"]), \
                    patch.object(acc, "prepare_test_harness", return_value=None):
                summary = acc.run_acceptance(
                    root, tests,
                    web_port=3000, extra_ports=[8080],
                    node_ids=["REQ-1", "REQ-9"],
                    free_port=lambda port: None, log=lambda m: None,
                    tail=lambda t, n=999: t[-n:], deadline=float("inf"),
                )
        self.assertFalse(summary["passed"])
        self.assertTrue(summary["all_specs_green"])
        self.assertEqual(summary["passed_nodes"], ["REQ-1"])
        self.assertEqual(summary["unknown"], ["REQ-9"])
        self.assertEqual(summary["evidence_failed"], [])

    def test_no_json_falls_back_to_exit_code(self):
        with tempfile.TemporaryDirectory() as dir_name:
            root = Path(dir_name)
            tests = self._write_deliverable(root)

            def fake_run(argv, **kwargs):
                return SimpleNamespace(returncode=0, stdout="ok", stderr="")

            with patch.object(acc, "wait_bound", return_value=True), \
                    patch.object(acc.subprocess, "Popen", return_value=_Proc()), \
                    patch.object(acc.subprocess, "run", side_effect=fake_run), \
                    patch.object(acc, "playwright_argv", return_value=["playwright"]), \
                    patch.object(acc, "prepare_test_harness", return_value=None):
                summary = acc.run_acceptance(
                    root, tests,
                    web_port=3000, extra_ports=[], node_ids=["REQ-1"],
                    free_port=lambda port: None, log=lambda m: None,
                    tail=lambda t, n=999: t[-n:], deadline=float("inf"),
                )
        self.assertTrue(summary["fallback"])
        self.assertTrue(summary["passed"])
        self.assertIn("exit code", summary["message"])

    def test_missing_runner_reports_unavailable(self):
        with tempfile.TemporaryDirectory() as dir_name:
            root = Path(dir_name)
            tests = self._write_deliverable(root)
            with patch.object(acc, "wait_bound", return_value=True), \
                    patch.object(acc.subprocess, "Popen", return_value=_Proc()), \
                    patch.object(acc.subprocess, "run", return_value=SimpleNamespace(
                        returncode=1,
                        stdout="Please install @playwright/test package",
                        stderr="",
                    )), \
                    patch.object(acc, "playwright_argv", return_value=["playwright"]), \
                    patch.object(acc, "prepare_test_harness", return_value=None):
                summary = acc.run_acceptance(
                    root, tests,
                    web_port=3000, extra_ports=[], node_ids=["REQ-1"],
                    free_port=lambda port: None, log=lambda m: None,
                    tail=lambda t, n=999: t[-n:], deadline=float("inf"),
                )
        self.assertFalse(summary["available"])
        self.assertIsNone(summary["passed"])

    def test_harness_error_short_circuits(self):
        with tempfile.TemporaryDirectory() as dir_name:
            root = Path(dir_name)
            tests = self._write_deliverable(root)
            with patch.object(acc, "wait_bound", return_value=True), \
                    patch.object(acc.subprocess, "Popen", return_value=_Proc()), \
                    patch.object(acc, "prepare_test_harness",
                                 return_value="tests harness install failed: network"):
                summary = acc.run_acceptance(
                    root, tests,
                    web_port=3000, extra_ports=[8080], node_ids=["REQ-1"],
                    free_port=lambda port: None, log=lambda m: None,
                    tail=lambda t, n=999: t[-n:], deadline=float("inf"),
                )
        self.assertFalse(summary["available"])
        self.assertIn("harness install failed", summary["message"])
