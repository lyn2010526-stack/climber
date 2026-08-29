"""Schema contracts for persisted unified Run data."""

from __future__ import annotations

from app.storage.database import RunEventRecord, Turn


def test_turn_contains_unified_run_fields():
    columns = Turn.__table__.c

    assert {"user_id", "agent_id", "kind", "trace_id", "last_sequence", "execution_token", "parent_run_id"} <= set(
        columns.keys()
    )
    assert columns.kind.default.arg == "agent_chat"
    assert columns.last_sequence.default.arg == 0
    assert columns.execution_token.default.arg == 0


def test_run_event_schema_has_run_scoped_idempotency_constraints():
    columns = RunEventRecord.__table__.c

    assert {
        "id",
        "run_id",
        "event_id",
        "sequence",
        "event_type",
        "data",
        "created_at",
        "trace_id",
        "checkpoint_id",
        "execution_token",
    } <= set(columns.keys())

    unique_constraints = {
        tuple(constraint.columns.keys())
        for constraint in RunEventRecord.__table__.constraints
        if constraint.name in {"uq_run_events_run_event", "uq_run_events_run_sequence"}
    }
    assert unique_constraints == {("run_id", "event_id"), ("run_id", "sequence")}
