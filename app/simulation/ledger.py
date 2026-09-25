"""Experiment ledger — append-only JSONL persistence of the full loop.

Mirrors AgentLaboratory's reproducible run-record requirement: every
round, every attempt, every parameter set, output, probe verdict and
reviewer note is written to a line-oriented JSON file so an experiment
can be replayed or audited end-to-end.

Writes are serialized through a lock so concurrent experiment rounds
(the harness runs experiments in parallel) never interleave lines.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any

from app.simulation.models import ExperimentAttempt, ExperimentReport

_LEDGER_SCHEMA = "simulation-ledger-1.0"


class ExperimentLedger:
    """Append-only JSONL ledger for a single experiment run."""

    def __init__(self, directory: str | os.PathLike[str], run_id: str | None = None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id or str(uuid.uuid4())[:12]
        self.path = self.directory / f"run-{self.run_id}.jsonl"
        self._lock = threading.Lock()

    def record_goal(self, goal: str, plan: list[dict[str, Any]]) -> None:
        """Write the initial plan for traceability."""
        self._write({"type": "goal", "goal": goal, "plan": plan})

    def record_attempt(self, attempt: ExperimentAttempt) -> None:
        """Write a single attempt record."""
        self._write({
            "type": "attempt",
            "round": attempt.round,
            "spec_id": attempt.spec_id,
            "tool_name": attempt.tool_name,
            "parameters": attempt.parameters,
            "output": attempt.output,
            "success": attempt.success,
            "error": attempt.error,
            "duration_ms": attempt.duration_ms,
            "probe": attempt.probe.model_dump(),
            "verdict": attempt.verdict.value if attempt.verdict else None,
            "reviewer_note": attempt.reviewer_note,
            "timestamp": attempt.timestamp,
        })

    def record_report(self, report: ExperimentReport) -> None:
        """Write the final per-experiment report."""
        self._write({
            "type": "report",
            "spec": report.spec.model_dump(),
            "rounds_used": report.rounds_used,
            "max_rounds": report.max_rounds,
            "accepted_parameters": (
                report.accepted_attempt.parameters
                if report.accepted_attempt else None
            ),
            "accepted_output": (
                report.accepted_attempt.output
                if report.accepted_attempt else None
            ),
        })

    def record_plan_round(
        self,
        round_number: int,
        tool_name: str,
        plan_total: int,
        accepted: int,
        rejected: int,
        satisfied: bool,
        feedback: str,
    ) -> None:
        """Write one orchestrator plan-round summary."""
        self._write({
            "type": "plan_round",
            "round_number": round_number,
            "tool_name": tool_name,
            "plan_total": plan_total,
            "accepted": accepted,
            "rejected": rejected,
            "satisfied": satisfied,
            "feedback": feedback,
        })

    def record_final_report(self, final_report: dict[str, Any]) -> None:
        """Write the orchestrator's final synthesized report."""
        self._write({
            "type": "final_report",
            "final_report": final_report,
        })

    def _write(self, record: dict[str, Any]) -> None:
        record["_schema"] = _LEDGER_SCHEMA
        record["run_id"] = self.run_id
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with self._lock:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(line)

    def read_all(self) -> list[dict[str, Any]]:
        """Read all records in write order."""
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        with open(self.path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records
