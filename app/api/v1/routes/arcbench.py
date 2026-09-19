"""ARC-Bench submission status API — read-only queries for the competition console.

Exposes the currently-visible state of the ARC-Bench adapter run derived from
real on-disk artifacts:

* ``<output_dir>/.arc/runner-events.jsonl`` — runtime + per-node phase events
* ``<output_dir>/run_summary.json`` — end-of-run metrics (tokens, acceptance)
* ``<output_dir>/.arc/traceability/`` — trace artifacts
* ``<root>/dist/climber-arcbench-*.zip`` — packaged submission bundle

Only GET operations are exposed; nothing here mutates the run or the repo.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter

from app.schemas.api_v1.arcbench import (
    ArcBenchAcceptance,
    ArcBenchEvent,
    ArcBenchStatus,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/arcbench", tags=["arcbench"])

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_RUN_DIR = _PROJECT_ROOT / "workspace"
_PACK_DIR = _PROJECT_ROOT / "dist"

_MAX_EVENTS = 20


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _latest_run_dir() -> Path | None:
    """Locate the most recent ARC-Bench output directory.

    The adapter defaults to ``<cwd>/workspace/run-<ts>`` and honours
    ``ARCBENCH_TEMPLATE_DIR`` as an override; both are considered here.
    """
    candidates: list[Path] = []
    env_dir = os.environ.get("ARCBENCH_TEMPLATE_DIR", "").strip()
    if env_dir:
        candidate = Path(env_dir).expanduser()
        if candidate.is_dir():
            candidates.append(candidate)
    if _RUN_DIR.is_dir():
        candidates.extend(p for p in _RUN_DIR.iterdir() if p.is_dir() and p.name.startswith("run-"))
    if not candidates:
        return None
    return max(candidates, key=_mtime)


def _read_events(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / ".arc" / "runner-events.jsonl"
    if not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError as exc:
        logger.warning("arcbench_events_read_failed", path=str(path), error=str(exc))
        return []
    return events


def _read_run_summary(run_dir: Path) -> dict[str, Any] | None:
    path = run_dir / "run_summary.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("arcbench_summary_read_failed", path=str(path), error=str(exc))
        return None


def _phase_label(phase: str) -> str:
    return {"implement": "implementation"}.get(phase, phase)


def _derive_phase(events: list[dict[str, Any]], summary: dict[str, Any] | None) -> tuple[str, str]:
    """Map runner events + run summary to a coarse pipeline stage + detail."""
    runner_states = [e for e in events if e.get("type") == "runner_state"]

    def _runner_state() -> str | None:
        return runner_states[-1].get("state") if runner_states else None

    node_events = [e for e in events if e.get("type") == "requirement_state"]

    def _pipeline_phase() -> str | None:
        for phase in ("test", "implement", "design"):
            if any(e.get("phase") == phase for e in node_events):
                return _phase_label(phase)
        return None

    if _runner_state() == "failed":
        return "failed", str(runner_states[-1].get("message") or "run failed")
    if summary:
        note = str(summary.get("acceptance") or "")
        if summary.get("rehearsal_error"):
            detail = "startup rehearsal failed; submitted as-is"
            return "rehearsal", f"{detail}; {note}" if note else detail
        return "acceptance", note or "run completed"
    if _runner_state() == "completed":
        return "completed", str(runner_states[-1].get("message") or "run completed")
    pipeline = _pipeline_phase()
    if pipeline:
        return pipeline, "requirement phase in progress"
    if _runner_state():
        return "running", f"runner state '{_runner_state()}'"
    return "design", "planning / design in progress"


def _build_acceptance(events: list[dict[str, Any]], summary: dict[str, Any] | None) -> ArcBenchAcceptance:
    test_nodes = [
        e for e in events
        if e.get("type") == "requirement_state" and e.get("phase") == "test"
    ]
    passed = sum(1 for e in test_nodes if e.get("status") == "passed")
    failed = sum(1 for e in test_nodes if e.get("status") == "failed")
    ran = passed + failed > 0
    note = str((summary or {}).get("acceptance") or "")
    if not ran and not note:
        note = "acceptance tests not run or no artifacts yet"
    return ArcBenchAcceptance(
        ran=ran,
        passed=passed,
        failed=failed,
        unverified=max(len(test_nodes) - passed - failed, 0),
        note=note,
    )


def _latest_pack_artifact() -> Path | None:
    if not _PACK_DIR.is_dir():
        return None
    zips = sorted(_PACK_DIR.glob("climber-arcbench-*.zip"), key=_mtime, reverse=True)
    return zips[0] if zips else None


@router.get("/status", response_model=ArcBenchStatus)
async def arcbench_status() -> ArcBenchStatus:
    """Return the state of the most recent ARC-Bench run (read-only)."""
    run_dir = _latest_run_dir()
    if run_dir is None:
        return ArcBenchStatus(available=False, message="尚未运行,尚未找到任何 ARC-Bench 输出目录")

    events = _read_events(run_dir)
    summary = _read_run_summary(run_dir)
    phase, phase_detail = _derive_phase(events, summary)
    trace_path = run_dir / ".arc" / "traceability"
    pack = _latest_pack_artifact()

    last_events = []
    for raw in events[-_MAX_EVENTS:]:
        payload = dict(raw)
        event = {"type": str(payload.pop("type", "")), "timestamp": str(payload.pop("timestamp", "") or "")}
        event["data"] = payload
        last_events.append(ArcBenchEvent(**event))

    updated_at: str | None = None
    if events and events[-1].get("timestamp"):
        updated_at = str(events[-1]["timestamp"])

    return ArcBenchStatus(
        available=True,
        message="ARC-Bench run artifacts detected",
        output_dir=str(run_dir),
        phase=phase,
        phase_detail=phase_detail,
        trace_path=str(trace_path) if trace_path.exists() else str(trace_path.parent),
        trace_exists=trace_path.exists(),
        acceptance=_build_acceptance(events, summary),
        last_events=last_events,
        pack_artifact=str(pack) if pack else None,
        pack_exists=pack is not None,
        updated_at=updated_at,
    )
