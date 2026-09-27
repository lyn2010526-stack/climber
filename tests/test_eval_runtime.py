"""The evaluation runtime: real measurement, and honest inconclusive reporting.

The property under test is not "does a run succeed" but "does a run only ever
report a number it actually measured". The suite therefore has four
first-class cases, in the order they matter:

1. A real adapter run against a trivial local target produces a real score
   computed from real Playwright spec outcomes.
2. A run whose infrastructure is unavailable yields ``inconclusive`` with a
   reason and **no** score, at row level and in the aggregate.
3. A missing or corrupt report yields ``inconclusive``, never a default pass.
4. Results persist and re-read identically, including the inconclusive rows.

The remaining tests cover the registry, the workdir guard, the API surface, and
the type-level invariants that make a fabricated score unrepresentable.

Tests that need a browser-free Playwright runner use the adapter's own
``request``-fixture detection: a spec that never opens a page is measured for
real without any browser binary. When no node Playwright runner is present the
suite proves the inconclusive path instead, which is the property that matters
most.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.eval import EvaluationService, TargetNotFoundError, Verdict
from app.eval.errors import EvaluationError, TargetSetupError
from app.eval.persistence import METHOD_INCONCLUSIVE, load_stored_result
from app.eval.scoring import build_score_table
from app.eval.service import RUNS_DIRNAME, RunRequest
from app.eval.targets import TargetSpec, get_target, register, unregister
from app.eval.targets_arcbench import (
    ArcbenchTarget,
    _resolve_ports,
    node_ids_from_requirements,
    port_is_free,
    read_arc_events,
)
from app.eval.types import (
    CapabilityCheck,
    CapabilityState,
    CaseRow,
    RunStatus,
    ScoreTable,
    TargetRunResult,
    capability_from_mapping,
)
from app.storage import async_session
from app.storage.database import Agent
from app.storage.models_eval import EvalDataset, EvalResult, EvalRun

NODE_IDS = ["REQ-1", "REQ-2", "REQ-3"]

# A spec that only uses the `request` fixture drives Playwright's HTTP stack and
# never launches a browser, so it can be measured for real in an environment
# with no browser binaries. The port comes from the platform's own channel.
PASSING_SPEC = """
import { test, expect } from "@playwright/test";
const PORT = process.env.ARCBENCH_WEB_PORT || process.env.PORT;
test("REQ-1 health endpoint responds with ok", async ({ request }) => {
  const response = await request.get(`http://127.0.0.1:${PORT}/api/health`);
  expect(response.ok()).toBeTruthy();
  expect((await response.json()).status).toBe("ok");
});
"""

PASSING_SPEC_2 = """
import { test, expect } from "@playwright/test";
const PORT = process.env.ARCBENCH_WEB_PORT || process.env.PORT;
test("REQ-2 calc endpoint returns 42", async ({ request }) => {
  const response = await request.get(`http://127.0.0.1:${PORT}/api/calc`);
  expect(response.ok()).toBeTruthy();
  expect((await response.json()).value).toBe(42);
});
"""

FAILING_SPEC = """
import { test, expect } from "@playwright/test";
test("REQ-1 health endpoint responds with ok", async ({ request }) => {
  const response = await request.get("http://127.0.0.1:1/definitely-not-listening");
  expect(response.ok()).toBeTruthy();
});
"""

BROWSER_SPEC = """
import { test, expect } from "@playwright/test";
test("REQ-1 renders the page", async ({ page }) => {
  await page.goto("http://127.0.0.1:1/");
  await expect(page.locator("h1")).toBeVisible();
});
"""

SERVER_JS = """
const http = require("http");
const port = Number(process.env.PORT || 3000);
const server = http.createServer((req, res) => {
  res.setHeader("Content-Type", "application/json");
  if (req.url === "/api/health") { res.end(JSON.stringify({ status: "ok" })); return; }
  if (req.url === "/api/calc") { res.end(JSON.stringify({ value: 42 })); return; }
  res.statusCode = 404;
  res.end(JSON.stringify({ error: "not found" }));
});
server.listen(port, "127.0.0.1");
"""

BACKEND_PACKAGE = json.dumps(
    {"name": "trivial-backend", "private": True, "version": "1.0.0", "scripts": {"start": "node server.js"}}
)

REQUIREMENTS_YAML = """
root:
  id: REQ-ROOT
  name: trivial requirement tree
  type: FOLDER
  children:
    - id: REQ-1
      name: health endpoint responds ok
      type: ATOMIC
      description: GET /api/health returns status ok
    - id: REQ-2
      name: calc endpoint returns 42
      type: ATOMIC
      description: GET /api/calc returns value 42
    - id: REQ-3
      name: node with no spec
      type: ATOMIC
      description: no official spec covers this node
"""


# --------------------------------------------------------------------- helpers


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
def node_playwright_runner() -> str:
    """Install a node Playwright runner once, or skip the run that needs it."""
    if not shutil.which("npm"):
        pytest.skip("npm is unavailable, so no node Playwright runner can be prepared")
    root = Path(__file__).resolve().parent / ".eval_fixtures" / "playwright"
    runner = root / "node_modules" / ".bin" / "playwright"
    if not runner.is_file():
        root.mkdir(parents=True, exist_ok=True)
        (root / "package.json").write_text(json.dumps({"name": "eval-fixture", "private": True}))
        completed = subprocess.run(
            ["npm", "install", "--no-audit", "--no-fund", "@playwright/test"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=600,
        )
        if completed.returncode != 0 or not runner.is_file():
            pytest.skip(f"could not install a node Playwright runner: {completed.stderr[-200:]}")
    return str(runner)


def _make_deliverable(root: Path, *, with_backend: bool = True) -> Path:
    deliverable = root / "deliverable"
    (deliverable / "frontend").mkdir(parents=True, exist_ok=True)
    (deliverable / "frontend" / "index.html").write_text("<html></html>")
    if with_backend:
        backend = deliverable / "backend"
        backend.mkdir(parents=True, exist_ok=True)
        (backend / "server.js").write_text(SERVER_JS)
        (backend / "package.json").write_text(BACKEND_PACKAGE)
    else:
        # A frontend-only deliverable: the grader cannot start it.
        (deliverable / "frontend" / "README").write_text("no backend here")
    return deliverable


def _make_tests_dir(root: Path, specs: dict[str, str], runner: str | None) -> Path:
    tests = root / "tests"
    tests.mkdir(parents=True, exist_ok=True)
    (tests / "package.json").write_text(json.dumps({"name": "official-tests", "private": True}))
    for name, body in specs.items():
        (tests / name).write_text(body)
    if runner:
        link = tests / "node_modules"
        target = Path(runner).parents[1]
        if not link.exists():
            try:
                link.symlink_to(target)
            except OSError:
                pytest.skip("could not link the node Playwright runner into the tests dir")
    return tests


def _make_requirements(root: Path) -> Path:
    (root / "requirements.yaml").write_text(REQUIREMENTS_YAML)
    return root


async def _agent_id(db) -> str:
    agent = Agent(id=str(uuid4()), user_id="default-user", name="eval-test", provider="openai", model_id="none")
    db.add(agent)
    await db.commit()
    return agent.id


async def _dataset_id(db) -> str:
    dataset = EvalDataset(user_id="default-user", name="eval-test", description="", data_json="[]")
    db.add(dataset)
    await db.commit()
    return dataset.id


def _request(root: Path, *, dataset_id: str, agent_id: str, run_name: str,
             service: EvaluationService, deliverable: Path | None = None) -> RunRequest:
    return RunRequest(
        target="arcbench",
        spec={"note": run_name},
        config={
            "deliverable_dir": str(deliverable or _make_deliverable(root)),
            "tests_dir": str(root / "tests"),
            "requirements_dir": str(_make_requirements(root)),
            "web_port": _free_port(),
            "smoke_port": _free_port(),
            "timeout": 180.0,
        },
        agent_id=agent_id,
        user_id="default-user",
        dataset_id=dataset_id,
        workdir=str(service.runs_root / run_name),
    )


@pytest.fixture
def service(tmp_path) -> EvaluationService:
    """A service whose run artifacts live in this test's own directory."""
    return EvaluationService(runs_root=tmp_path / RUNS_DIRNAME)


@pytest_asyncio.fixture
async def agent_id():
    async with async_session() as db:
        return await _agent_id(db)


@pytest_asyncio.fixture
async def dataset_id():
    async with async_session() as db:
        return await _dataset_id(db)


# ------------------------------------------------------------------- case one


async def test_real_adapter_run_against_trivial_target_produces_real_score(
    tmp_path, node_playwright_runner, agent_id, dataset_id, service
):
    """A real run: node backend on a real port, real Playwright specs, real score.

    The score is not asserted to a hardcoded number. It is derived from the
    adapter's per-spec outcomes, and REQ-3 is expected to come back
    inconclusive because no spec mentions it, which is what makes the aggregate
    coverage honest.
    """
    root = tmp_path / "measured"
    _make_tests_dir(root, {"req-1.spec.ts": PASSING_SPEC, "req-2.spec.ts": PASSING_SPEC_2}, node_playwright_runner)

    request = _request(root, dataset_id=dataset_id, agent_id=agent_id, run_name="measured", service=service)
    async with async_session() as db:
        table = await service.run(db, request)

    assert table.status.value == "measured"
    assert table.total_cases == 3
    assert table.scored_cases == 2, "both passing specs must produce evidence"
    assert table.passed_cases == 2
    assert table.failed_cases == 0
    assert table.score == 1.0
    assert table.pass_rate == 1.0
    assert table.coverage == pytest.approx(2 / 3)

    # The score is a projection of the adapter's own verdicts, not a constant.
    for row in table.rows:
        if row.case_id in ("REQ-1", "REQ-2"):
            assert row.verdict is Verdict.PASSED
            assert row.score == 1.0
        else:
            assert row.verdict is Verdict.INCONCLUSIVE
            assert row.score is None
            assert "no acceptance spec" in row.reason

    # The adapter's own summary is retained as evidence.
    summary = table.evidence.summary
    assert summary["ran"] is True
    assert summary["available"] is True
    assert summary["fallback"] is False
    assert summary["specs_detail"], "per-spec outcomes must be retained"
    assert len(summary["specs_detail"]) == 2
    assert all(entry["passed"] for entry in summary["specs_detail"])

    # A real .arc event stream exists for this run.
    events = read_arc_events(Path(request.workdir) / ".arc" / "runner-events.jsonl")
    assert any(event.get("state") == "eval_run_finished" for event in events)


async def test_failing_spec_produces_a_real_failed_verdict_not_a_default(
    tmp_path, node_playwright_runner, agent_id, dataset_id, service
):
    """A genuinely failing spec is reported as failed, which is a measurement."""
    root = tmp_path / "failing"
    _make_tests_dir(root, {"req-1.spec.ts": FAILING_SPEC}, node_playwright_runner)

    request = _request(root, dataset_id=dataset_id, agent_id=agent_id, run_name="failing", service=service)
    async with async_session() as db:
        table = await service.run(db, request)

    row = table.row_for("REQ-1")
    assert row is not None
    assert row.verdict is Verdict.FAILED
    assert row.score == 0.0
    assert table.failed_cases == 1
    assert table.pass_rate == 0.0
    # The run still measured something, so it is not inconclusive overall.
    assert table.status.value == "measured"


# ------------------------------------------------------------------ case two


async def test_unavailable_infrastructure_yields_inconclusive_with_no_score(
    tmp_path, agent_id, dataset_id, service
):
    """No backend to start: every case is inconclusive and the aggregate is null.

    This is the property that matters most. A run that could not measure
    anything must not be reported as a score of 0, which would read as "every
    requirement failed".
    """
    root = tmp_path / "no-backend"
    _make_tests_dir(root, {"req-1.spec.ts": PASSING_SPEC}, None)
    deliverable = _make_deliverable(root, with_backend=False)

    request = _request(
        root,
        dataset_id=dataset_id,
        agent_id=agent_id,
        run_name="no-backend",
        service=service,
        deliverable=deliverable,
    )
    async with async_session() as db:
        table = await service.run(db, request)

    assert table.status.value == "inconclusive"
    assert table.is_inconclusive is True
    assert table.scored_cases == 0
    assert table.score is None, "an unmeasured run must not report a score"
    assert table.pass_rate is None, "an unmeasured run must not report a pass rate"
    assert table.coverage == 0.0
    assert table.total_cases == 3
    assert table.inconclusive_cases == 3
    for row in table.rows:
        assert row.verdict is Verdict.INCONCLUSIVE
        assert row.score is None
        assert row.reason, "every inconclusive row must carry a reason"

    reasons = " ".join(table.inconclusive_reasons)
    assert "deliverable_backend" in reasons
    assert "backend/package.json" in reasons

    # The reason is recorded in the evidence too, so it survives a re-read.
    assert table.evidence.summary.get("preflight")


async def test_missing_specs_yield_inconclusive_before_anything_executes(
    tmp_path, agent_id, dataset_id, service
):
    """No official specs at all: the adapter's own unavailable path fires."""
    root = tmp_path / "no-specs"
    _make_tests_dir(root, {}, None)

    request = _request(root, dataset_id=dataset_id, agent_id=agent_id, run_name="no-specs", service=service)
    async with async_session() as db:
        table = await service.run(db, request)

    assert table.status.value == "inconclusive"
    assert table.score is None
    assert table.pass_rate is None
    assert all(row.score is None for row in table.rows)
    assert any("acceptance" in reason for reason in table.inconclusive_reasons)

    # Preflight stopped the run before the adapter was reached, and the reason
    # is recorded rather than silently dropped.
    assert "acceptance_specs" in " ".join(table.inconclusive_reasons)
    assert table.evidence.summary.get("preflight")
    # The adapter recorded no pass, and it was never even invoked.
    assert table.evidence.summary["adapter_invoked"] is False
    assert table.evidence.summary["ran"] is False
    assert table.evidence.summary["passed"] is None


async def test_busy_grading_port_is_inconclusive_not_a_failure(tmp_path, agent_id, dataset_id, service):
    """A port the grader cannot bind is an infrastructure problem, not a bug."""
    root = tmp_path / "busy-port"
    _make_tests_dir(root, {"req-1.spec.ts": PASSING_SPEC}, None)

    request = _request(root, dataset_id=dataset_id, agent_id=agent_id, run_name="busy-port", service=service)
    holder = socket.socket()
    holder.bind(("127.0.0.1", 0))
    holder.listen(1)
    request.config["web_port"] = holder.getsockname()[1]
    try:
        async with async_session() as db:
            table = await service.run(db, request)
    finally:
        holder.close()

    assert table.status.value == "inconclusive"
    assert table.score is None
    assert any("grading_port" in reason for reason in table.inconclusive_reasons)


# ---------------------------------------------------------------- case three


def test_exit_code_only_attribution_is_inconclusive_not_a_pass():
    """A missing usable report must never become a pass.

    The adapter itself falls back to the process exit code when no JSON report
    is produced (``adapters/arcbench/acceptance.py:332-345``). This runtime
    treats that outcome as inconclusive, because a usable per-spec report is the
    standard it holds itself to.
    """
    target = ArcbenchTarget()
    verdicts, reasons, scored, message = target._verdicts_from_summary(
        {
            "ran": True,
            "available": True,
            "passed": True,
            "all_specs_green": True,
            "passed_nodes": NODE_IDS,
            "evidence_failed": [],
            "unknown": [],
            "fallback": True,
            "specs_detail": [],
            "message": "attributed by playwright exit code (no JSON report): ",
        },
        NODE_IDS,
    )

    assert scored is False
    assert set(verdicts.values()) == {Verdict.INCONCLUSIVE}
    assert "no usable per-spec report" in message
    assert all(reason for reason in reasons.values())


def test_unavailable_summary_is_inconclusive_even_though_the_adapter_ran():
    """``ran: True`` does not make a run conclusive when ``available`` is false."""
    target = ArcbenchTarget()
    verdicts, reasons, scored, message = target._verdicts_from_summary(
        {
            "ran": True,
            "available": False,
            "passed": None,
            "all_specs_green": False,
            "passed_nodes": [],
            "evidence_failed": [],
            "unknown": NODE_IDS,
            "fallback": False,
            "specs_detail": [],
            "message": "playwright unavailable: [Errno 2] No such file or directory",
        },
        NODE_IDS,
    )

    assert scored is False
    assert set(verdicts.values()) == {Verdict.INCONCLUSIVE}
    assert "playwright unavailable" in message
    assert all(reason for reason in reasons.values())


def test_corrupt_report_text_yields_no_parsed_specs():
    """A corrupt report body produces no per-spec evidence to score."""
    from app.eval.targets_arcbench import load_adapter

    acceptance = load_adapter().acceptance
    assert acceptance.parse_playwright_report(None) is None
    assert acceptance.parse_playwright_report({"suites": []}) is None
    assert acceptance.parse_playwright_report({"no_suites_key": True}) is None
    assert acceptance.try_json_from_text("") is None
    assert acceptance.try_json_from_text("not json at all") is None
    assert acceptance.try_json_from_text('{"suites": [') is None


async def test_report_that_never_ran_is_inconclusive():
    """A summary with ``ran: False`` produced no measurement."""
    target = ArcbenchTarget()
    verdicts, _reasons, scored, _message = target._verdicts_from_summary(
        {"ran": False, "available": True, "passed": None, "message": "nothing started"},
        NODE_IDS,
    )
    assert scored is False
    assert set(verdicts.values()) == {Verdict.INCONCLUSIVE}


async def test_uncovered_node_is_inconclusive_not_failed(tmp_path, agent_id, dataset_id, service):
    """A node with no spec is unknown, so it is neither passed nor failed."""
    root = tmp_path / "partial"
    _make_tests_dir(root, {"req-1.spec.ts": PASSING_SPEC}, None)

    request = _request(root, dataset_id=dataset_id, agent_id=agent_id, run_name="partial", service=service)
    async with async_session() as db:
        table = await service.run(db, request)

    for case_id in ("REQ-2", "REQ-3"):
        row = table.row_for(case_id)
        assert row.verdict is Verdict.INCONCLUSIVE
        assert row.score is None
    assert table.inconclusive_reasons
    assert table.coverage < 1.0


# ----------------------------------------------------------------- case four


async def test_results_persist_and_re_read_identically(
    tmp_path, node_playwright_runner, agent_id, dataset_id, service
):
    """A stored run re-reads to the same table, inconclusive rows included."""
    root = tmp_path / "persist"
    _make_tests_dir(root, {"req-1.spec.ts": PASSING_SPEC, "req-2.spec.ts": PASSING_SPEC_2}, node_playwright_runner)

    request = _request(root, dataset_id=dataset_id, agent_id=agent_id, run_name="persist", service=service)
    async with async_session() as db:
        original = await service.run(db, request)
        run_id = original.run_id

    async with async_session() as db:
        reread = await service.get(db, run_id)

    assert reread.to_dict() == original.to_dict()
    assert reread.score == original.score
    assert reread.pass_rate == original.pass_rate
    assert [row.verdict for row in reread.rows] == [row.verdict for row in original.rows]
    assert [row.score for row in reread.rows] == [row.score for row in original.rows]

    async with async_session() as db:
        run = await db.get(EvalRun, run_id)
        assert run is not None
        assert run.total_cases == original.total_cases
        assert run.passed_cases == original.passed_cases
        assert run.failed_cases == original.failed_cases
        assert run.average_score == original.score
        assert run.pass_rate == original.pass_rate

        results = (
            (await db.execute(select(EvalResult).where(EvalResult.run_id == run_id))).scalars().all()
        )
        assert len(results) == original.total_cases
        by_case = {row.case_id: row for row in results}
        assert by_case["REQ-1"].scoring_method != METHOD_INCONCLUSIVE
        assert by_case["REQ-3"].scoring_method == METHOD_INCONCLUSIVE
        # The verdict travels with the row so no aggregate can silently count it.
        assert json.loads(by_case["REQ-3"].reasoning)["verdict"] == "inconclusive"
        assert json.loads(by_case["REQ-1"].reasoning)["verdict"] == "passed"


async def test_inconclusive_run_round_trips_with_a_null_aggregate(
    tmp_path, agent_id, dataset_id, service
):
    """An unmeasured run reads back as unmeasured, not as a zero score."""
    root = tmp_path / "persist-inconclusive"
    _make_tests_dir(root, {"req-1.spec.ts": PASSING_SPEC}, None)
    deliverable = _make_deliverable(root, with_backend=False)

    request = _request(
        root,
        dataset_id=dataset_id,
        agent_id=agent_id,
        run_name="persist-inconclusive",
        service=service,
        deliverable=deliverable,
    )
    async with async_session() as db:
        original = await service.run(db, request)

    async with async_session() as db:
        reread = await service.get(db, original.run_id)
        stored = await load_stored_result(db, original.run_id)

    assert reread.score is None
    assert reread.pass_rate is None
    assert reread.status.value == "inconclusive"
    assert reread.to_dict() == original.to_dict()
    assert stored.inconclusive is True
    assert stored.scored is False
    assert all(verdict is Verdict.INCONCLUSIVE for verdict in stored.verdicts.values())

    async with async_session() as db:
        results = (
            (
                await db.execute(
                    select(EvalResult).where(EvalResult.run_id == original.run_id)
                )
            )
            .scalars()
            .all()
        )
    assert results
    assert all(row.scoring_method == METHOD_INCONCLUSIVE for row in results)


async def test_recomputation_from_evidence_is_stable():
    """The score table is a pure function of the evidence, so it reproduces."""
    result = TargetRunResult(
        target="arcbench",
        verdicts={"REQ-1": Verdict.PASSED, "REQ-2": Verdict.FAILED},
        reasons={"REQ-2": "spec failed"},
        scored=True,
        message="1 of 2 specs green",
        evidence={"inputs": {"a": 1}, "summary": {"specs": 2}},
    )
    first = build_score_table(result, fingerprint="fp")
    second = build_score_table(result, fingerprint="fp")
    assert first.to_dict() == second.to_dict()
    assert first.score == 0.5
    assert first.pass_rate == 0.5


# ------------------------------------------------------------------ registry


def test_arcbench_target_is_registered():
    target = get_target("arcbench")
    assert isinstance(target, ArcbenchTarget)
    assert "acceptance" in target.description.lower()
    names = [entry["name"] for entry in EvaluationService().describe_targets()]
    assert "arcbench" in names


def test_unknown_target_raises_with_the_registered_list():
    with pytest.raises(TargetNotFoundError) as excinfo:
        get_target("does-not-exist")
    assert "arcbench" in str(excinfo.value)


def test_registry_accepts_a_second_target():
    """A new target plugs in without touching the runtime."""

    class CountingTarget:
        name = "counting"
        description = "counts its own cases"

        def build(self, spec):
            return {"workdir": Path(spec.workdir)}

        def preflight(self, spec):
            return []

        def execute(self, spec):
            return TargetRunResult(
                target=self.name,
                verdicts={"CASE-A": Verdict.PASSED},
                scored=True,
                message="counted",
                evidence={"inputs": {}},
            )

    register(CountingTarget())
    try:
        assert "counting" in [entry["name"] for entry in EvaluationService().describe_targets()]
        assert get_target("counting").name == "counting"
    finally:
        unregister("counting")


# ------------------------------------------------------------- type invariants


def test_inconclusive_row_cannot_carry_a_score():
    with pytest.raises(ValueError, match="fabricated"):
        CaseRow(case_id="REQ-1", verdict=Verdict.INCONCLUSIVE, score=0.0)


def test_scored_row_must_carry_a_score():
    with pytest.raises(ValueError, match="carries no score"):
        CaseRow(case_id="REQ-1", verdict=Verdict.PASSED, score=None)


def test_empty_case_id_is_rejected():
    with pytest.raises(ValueError, match="case_id is required"):
        CaseRow(case_id="   ", verdict=Verdict.INCONCLUSIVE)


def test_unmeasured_table_reports_null_aggregates():
    rows = [CaseRow(case_id="A", verdict=Verdict.INCONCLUSIVE, reason="infra missing")]
    table = ScoreTable(run_id="r", target="t", status=RunStatus.INCONCLUSIVE, rows=rows)
    assert table.score is None
    assert table.pass_rate is None
    assert table.coverage == 0.0


def test_case_row_round_trips_and_drops_a_bogus_score():
    raw = {"case_id": "A", "verdict": "inconclusive", "score": 0.8, "reason": "r"}
    row = CaseRow.from_mapping(raw)
    assert row is not None
    assert row.score is None, "a stored score on an inconclusive row must be discarded"

    scored = CaseRow.from_mapping({"case_id": "B", "verdict": "passed", "score": 1.0})
    assert scored is not None
    assert scored.score == 1.0

    assert CaseRow.from_mapping({"verdict": "passed"}) is None
    assert CaseRow.from_mapping("nonsense") is None


def test_capability_from_mapping_tolerates_junk():
    checks = capability_from_mapping(
        [
            {"name": "a", "state": "available"},
            {"name": "b", "state": "not-a-state"},
            {"state": "available"},
            "nonsense",
        ]
    )
    assert [check.name for check in checks] == ["a", "b"]
    assert checks[1].state is CapabilityState.UNKNOWN


def test_blocking_capability_ignores_optional_ones():
    required = CapabilityCheck(name="r", state=CapabilityState.UNAVAILABLE, detail="gone", required=True)
    optional = CapabilityCheck(name="o", state=CapabilityState.UNAVAILABLE, detail="gone", required=False)
    assert required.blocking is True
    assert optional.blocking is False


# ------------------------------------------------------------- service guards


def test_workdir_outside_the_runs_root_is_refused(tmp_path, agent_id, dataset_id, service):
    request = RunRequest(
        target="arcbench",
        spec={},
        config={},
        agent_id=agent_id,
        user_id="default-user",
        dataset_id=dataset_id,
        workdir=str(tmp_path / "escape"),
    )
    with pytest.raises(EvaluationError, match="must live under"):
        service.resolve_workdir(request, get_target("arcbench"))


def test_target_setup_requires_real_directories(tmp_path, agent_id, dataset_id, service):
    request = RunRequest(
        target="arcbench",
        spec={},
        config={"deliverable_dir": str(tmp_path / "nope")},
        agent_id=agent_id,
        user_id="default-user",
        dataset_id=dataset_id,
        workdir=str(service.runs_root / "setup-test"),
    )
    spec = service.build_spec(get_target("arcbench"), request)
    with pytest.raises(TargetSetupError, match="deliverable_dir"):
        get_target("arcbench").build(spec)


def test_target_setup_recovers_from_a_self_conflicting_port_pair(tmp_path, agent_id, dataset_id, service):
    """A caller repeating one port gets a working run instead of an error.

    Two equal ports make the grader bind and smoke-test the same socket. The
    adapter re-allocates the smoke port so the run still measures something.
    """
    root = tmp_path / "ports"
    tests = _make_tests_dir(root, {"req-1.spec.ts": PASSING_SPEC}, None)
    request = RunRequest(
        target="arcbench",
        spec={},
        config={
            "deliverable_dir": str(_make_deliverable(root)),
            "tests_dir": str(tests),
            "requirements_dir": str(_make_requirements(root)),
            "web_port": 4000,
            "smoke_port": 4000,
        },
        agent_id=agent_id,
        user_id="default-user",
        dataset_id=dataset_id,
        workdir=str(service.runs_root / "ports-test"),
    )
    spec = service.build_spec(get_target("arcbench"), request)
    plan = get_target("arcbench").build(spec)
    assert plan["web_port"] == 4000
    assert plan["smoke_port"] != plan["web_port"]
    assert plan["smoke_port"] > 0


# ----------------------------------------------------------------- preflight


def test_preflight_reports_missing_browsers_for_a_browser_spec(tmp_path, node_playwright_runner):
    """A browser-driving spec with no binaries is reported as a real gap."""
    root = tmp_path / "browser-preflight"
    tests = _make_tests_dir(root, {"req-1.spec.ts": BROWSER_SPEC}, node_playwright_runner)
    target = ArcbenchTarget()
    plan = {
        "deliverable": _make_deliverable(root),
        "tests_dir": tests,
        "requirements_dir": _make_requirements(root),
        "web_port": _free_port(),
        "smoke_port": _free_port(),
        "node_ids": NODE_IDS,
        "timeout": 60.0,
        "clear_web_port": False,
    }
    checks = {check.name: check for check in target._preflight(plan).checks}

    assert checks["acceptance_specs"].state is CapabilityState.AVAILABLE
    assert checks["playwright_runner"].state is CapabilityState.AVAILABLE
    assert checks["playwright_browsers"].required is True
    assert "request fixture" not in checks["playwright_browsers"].detail

    if checks["playwright_browsers"].state is CapabilityState.UNAVAILABLE:
        assert checks["playwright_browsers"].detail
        assert "ms-playwright" in checks["playwright_browsers"].detail or "browser payload" in (
            checks["playwright_browsers"].detail
        )


def test_preflight_does_not_demand_browsers_for_a_request_only_spec(tmp_path, node_playwright_runner):
    """A spec that never opens a page genuinely needs no browser binary."""
    root = tmp_path / "request-preflight"
    tests = _make_tests_dir(root, {"req-1.spec.ts": PASSING_SPEC}, node_playwright_runner)
    target = ArcbenchTarget()
    plan = {
        "deliverable": _make_deliverable(root),
        "tests_dir": tests,
        "requirements_dir": _make_requirements(root),
        "web_port": _free_port(),
        "smoke_port": _free_port(),
        "node_ids": NODE_IDS,
        "timeout": 60.0,
        "clear_web_port": False,
    }
    checks = {check.name: check for check in target._preflight(plan).checks}
    assert checks["playwright_browsers"].required is False
    assert "request fixture" in checks["playwright_browsers"].detail


def test_preflight_flags_a_missing_backend(tmp_path):
    root = tmp_path / "preflight-no-backend"
    tests = _make_tests_dir(root, {"req-1.spec.ts": PASSING_SPEC}, None)
    target = ArcbenchTarget()
    plan = {
        "deliverable": _make_deliverable(root, with_backend=False),
        "tests_dir": tests,
        "requirements_dir": _make_requirements(root),
        "web_port": _free_port(),
        "smoke_port": _free_port(),
        "node_ids": NODE_IDS,
        "timeout": 60.0,
        "clear_web_port": False,
    }
    checks = {check.name: check for check in target._preflight(plan).checks}
    assert checks["deliverable_backend"].state is CapabilityState.UNAVAILABLE
    assert checks["deliverable_backend"].blocking is True


def test_read_arc_events_skips_unreadable_lines(tmp_path):
    path = tmp_path / "runner-events.jsonl"
    path.write_text('{"type": "runner_state", "state": "a"}\nnot json\n\n{"type": "runner_state"}\n')
    events = read_arc_events(path)
    assert len(events) == 2
    assert read_arc_events(tmp_path / "missing.jsonl") == []


def test_node_ids_are_read_with_the_adapter_own_parser(tmp_path, service):
    root = tmp_path / "reqs"
    root.mkdir()
    _make_requirements(root)
    target = ArcbenchTarget()
    plan = {
        "workdir": service.runs_root / "reqs-test",
        "deliverable": root,
        "tests_dir": root,
        "requirements_dir": root,
        "web_port": _free_port(),
        "smoke_port": _free_port(),
        "node_ids": [],
        "timeout": 60.0,
        "clear_web_port": False,
    }
    node_ids = node_ids_from_requirements(root)
    assert node_ids == NODE_IDS
    # A plan with no explicit node ids reads them from the requirement tree.
    plan["node_ids"] = node_ids
    assert target._preflight(plan).node_ids == NODE_IDS


# ---------------------------------------------------------------- API surface


@pytest.mark.integration
async def test_api_reports_inconclusive_rather_than_inventing_a_score(client, tmp_path):
    """The endpoint returns a real verdict with its reasons, not a stored number."""
    root = tmp_path / "api"
    _make_deliverable(root, with_backend=False)
    _make_tests_dir(root, {"req-1.spec.ts": PASSING_SPEC}, None)

    async with async_session() as db:
        agent = await _agent_id(db)
        dataset = await _dataset_id(db)

    response = await client.post(
        "/api/v1/eval/run",
        json={
            "target": "arcbench",
            "agent_id": agent,
            "dataset_id": dataset,
            "config": {
                "deliverable_dir": str(_make_deliverable(root, with_backend=False)),
                "tests_dir": str(root / "tests"),
                "requirements_dir": str(_make_requirements(root)),
                "web_port": _free_port(),
                "smoke_port": _free_port(),
                "timeout": 60.0,
            },
            "workdir": str(EvaluationService().runs_root / "api-inconclusive"),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "measured"
    assert body["status"] == "inconclusive"
    assert body["score"] is None
    assert body["pass_rate"] is None
    assert body["inconclusive_reasons"]
    assert all(row["score"] is None for row in body["rows"])
    assert "evidence" not in body

    reread = await client.get(f"/api/v1/eval/run/{body['run_id']}")
    assert reread.status_code == 200
    assert reread.json()["status"] == "inconclusive"
    assert reread.json()["score"] is None


@pytest.mark.integration
async def test_api_legacy_record_path_still_works(client, agent_id, dataset_id):
    """Existing callers that post a record without a target keep working."""
    response = await client.post(
        "/api/v1/eval/run",
        json={
            "agent_id": agent_id,
            "dataset_id": dataset_id,
            "total_cases": 4,
            "passed_cases": 3,
            "failed_cases": 1,
            "average_score": 0.75,
            "pass_rate": 0.75,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "reported"
    assert body["total_cases"] == 4
    assert body["average_score"] == 0.75


@pytest.mark.integration
async def test_api_lists_registered_targets(client):
    response = await client.get("/api/v1/eval/targets")
    assert response.status_code == 200
    names = [entry["name"] for entry in response.json()["targets"]]
    assert "arcbench" in names


@pytest.mark.integration
async def test_api_rejects_an_unknown_target(client, agent_id, dataset_id):
    response = await client.post(
        "/api/v1/eval/run",
        json={"target": "nope", "agent_id": agent_id, "dataset_id": dataset_id, "config": {}},
    )
    assert response.status_code == 404
    assert "arcbench" in response.json()["detail"]


@pytest.mark.integration
async def test_api_preflight_reports_capabilities(client, agent_id, dataset_id, tmp_path):
    root = tmp_path / "api-preflight"
    _make_tests_dir(root, {}, None)
    response = await client.post(
        "/api/v1/eval/run",
        json={
            "target": "arcbench",
            "preflight_only": True,
            "agent_id": agent_id,
            "dataset_id": dataset_id,
            "config": {
                "deliverable_dir": str(_make_deliverable(root)),
                "tests_dir": str(root / "tests"),
                "requirements_dir": str(_make_requirements(root)),
                "web_port": _free_port(),
                "smoke_port": _free_port(),
            },
            "workdir": str(EvaluationService().runs_root / "api-preflight-run"),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "preflight"
    names = {check["name"] for check in body["capabilities"]}
    assert "acceptance_specs" in names
    assert "playwright_browsers" in names


@pytest.mark.integration
async def test_api_missing_agent_is_404(client, dataset_id):
    response = await client.post(
        "/api/v1/eval/run",
        json={"target": "arcbench", "agent_id": str(uuid4()), "dataset_id": dataset_id, "config": {}},
    )
    assert response.status_code == 404


@pytest.mark.integration
async def test_api_agent_id_is_required(client, dataset_id):
    response = await client.post("/api/v1/eval/run", json={"dataset_id": dataset_id})
    assert response.status_code == 422
    assert "agent_id" in response.json()["detail"]


# ------------------------------------------------------------- no credentials


async def test_evidence_never_carries_credentials(tmp_path, agent_id, dataset_id, service):
    """Stored evidence is inputs and verdicts, never environment secrets."""
    root = tmp_path / "no-secrets"
    _make_tests_dir(root, {"req-1.spec.ts": PASSING_SPEC}, None)
    deliverable = _make_deliverable(root, with_backend=False)
    request = _request(
        root,
        dataset_id=dataset_id,
        agent_id=agent_id,
        run_name="no-secrets",
        service=service,
        deliverable=deliverable,
    )

    async with async_session() as db:
        table = await service.run(db, request)
    serialized = json.dumps(table.to_dict(), default=str)
    for secret_name in ("OPENAI_API_KEY", "MCAI_LLM_API_KEY", "USER_LLM_API_KEY"):
        assert secret_name not in serialized
    assert os.environ.get("OPENAI_API_KEY", "<unset>") not in serialized or "<unset>" in serialized


# ---------------------------------------------------------------------------
# Grading-port allocation
#
# A caller that does not care which port the grader binds should not have to
# guess one. These tests pin the three shapes an HTTP client actually sends:
# no ports at all, one port, and two explicit ports.
# ---------------------------------------------------------------------------


def _spec_with_config(**config: object) -> TargetSpec:
    return TargetSpec(target="arcbench", spec={}, config=dict(config))


def test_grading_ports_are_allocated_when_the_caller_omits_them():
    """A portless request is the common case and must simply work."""
    web_port, smoke_port = _resolve_ports(_spec_with_config())
    assert web_port > 0
    assert smoke_port > 0
    assert web_port != smoke_port
    assert port_is_free(web_port)
    assert port_is_free(smoke_port)


def test_an_explicit_web_port_is_honoured_and_gets_a_distinct_smoke_port():
    """Honouring one port must not silently move it."""
    web_port, smoke_port = _resolve_ports(_spec_with_config(web_port=41999))
    assert web_port == 41999
    assert smoke_port > 0
    assert smoke_port != web_port


def test_an_explicit_smoke_port_is_honoured_and_gets_a_distinct_web_port():
    web_port, smoke_port = _resolve_ports(_spec_with_config(smoke_port=41998))
    assert smoke_port == 41998
    assert web_port > 0
    assert web_port != smoke_port


def test_two_explicit_ports_are_passed_through_untouched():
    assert _resolve_ports(_spec_with_config(web_port=41997, smoke_port=41996)) == (41997, 41996)


def test_identical_explicit_ports_never_produce_a_self_conflicting_run():
    """Two equal ports would make the grader fight itself; re-allocate instead."""
    web_port, smoke_port = _resolve_ports(_spec_with_config(web_port=41995, smoke_port=41995))
    assert web_port == 41995
    assert smoke_port != web_port
    assert smoke_port > 0
