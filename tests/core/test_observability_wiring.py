"""Engine observability wiring.

``TraceCollector`` and ``AuditChain`` had no production writer, and both
defaulted to ``":memory:"``, so ``GET /observability/traces`` and
``GET /observability/audit`` always returned empty lists. The engine is the only
component that knows what happened during a run, so it now opens a span and
appends audit entries around ``_run_locked``.

These tests assert the wiring rather than re-testing the collectors, and they
check that instrumentation never breaks a run.
"""

from __future__ import annotations

import pytest

from app.core import agent_engine as engine_mod
from app.core.observability.api import (
    get_audit_chain,
    get_trace,
    get_trace_collector,
    list_audit_entries,
    list_traces,
)
from app.core.observability.audit import AuditChain
from app.core.observability.trace import TraceCollector


@pytest.fixture
def sinks(tmp_path):
    collector = TraceCollector(db_path=str(tmp_path / "traces.db"))
    audit = AuditChain(db_path=str(tmp_path / "audit.db"))
    engine_mod._observability_sinks = lambda: (collector, audit)
    yield collector, audit
    import app.core.observability.api as obs_api

    obs_api._trace_collector = None
    obs_api._audit_chain = None


class _Session:
    def __init__(self, session_id: str = "s-1") -> None:
        self.session_id = session_id


class _Event:
    def __init__(self, event_type: str, data: dict) -> None:
        self.type = event_type
        self.data = data


def _engine_with_events(events: list[_Event]) -> object:
    """Build a bare engine whose _run_locked yields a fixed event list."""
    engine = engine_mod.AgentEngine.__new__(engine_mod.AgentEngine)
    engine._session_locks = {}
    engine._sessions = {}

    async def _run_locked(session, message):
        for event in events:
            yield event

    engine._run_locked = _run_locked
    return engine


async def test_run_opens_a_span_and_records_events(sinks):
    collector, _ = sinks
    engine = _engine_with_events([_Event("text", {"content": "hi"})])

    async for _ in engine.run(_Session(), "hello"):
        pass

    traces = collector.list_traces(limit=10)
    assert traces, "a run must leave a trace behind"
    assert traces[0]["span_count"] >= 1
    spans = collector.get_trace(traces[0]["trace_id"])
    assert spans and all(hasattr(s, "operation") for s in spans)


async def test_run_writes_audit_entries(sinks):
    _, audit = sinks
    engine = _engine_with_events([_Event("done", {"tokens_used": 5})])

    async for _ in engine.run(_Session("s-audit"), "hello"):
        pass

    entries = audit.get_chain(limit=50)
    types = {entry.decision_type for entry in entries}
    assert "agent_run_start" in types
    assert "agent_run_end" in types


async def test_run_writes_alignment_checks(monkeypatch, sinks):
    calls: list[str] = []

    class _Tracker:
        def check_alignment(self, action: str) -> None:
            calls.append(action)

    monkeypatch.setattr(engine_mod, "_alignment_tracker", lambda: _Tracker())
    engine = _engine_with_events([_Event("done", {})])

    async for _ in engine.run(_Session("s-alignment"), "ship the release"):
        pass

    assert calls == ["ship the release"]


async def test_audit_records_the_failure_and_reraises(sinks):
    _, audit = sinks
    engine = _engine_with_events([])

    async def _boom(session, message):
        raise RuntimeError("engine exploded")
        yield  # pragma: no cover - generator marker

    engine._run_locked = _boom

    with pytest.raises(RuntimeError, match="engine exploded"):
        async for _ in engine.run(_Session("s-fail"), "hello"):
            pass

    types = {entry.decision_type for entry in audit.get_chain(limit=50)}
    assert "agent_run_error" in types


async def test_span_is_closed_with_error_status(sinks):
    collector, _ = sinks
    engine = _engine_with_events([])

    async def _boom(session, message):
        raise RuntimeError("nope")
        yield  # pragma: no cover - generator marker

    engine._run_locked = _boom

    with pytest.raises(RuntimeError):
        async for _ in engine.run(_Session("s-status"), "hello"):
            pass

    traces = collector.list_traces(limit=10)
    spans = collector.get_trace(traces[0]["trace_id"])
    assert any(span.status == "error" for span in spans)


async def test_missing_sinks_do_not_break_a_run():
    """Instrumentation must never be the reason a task fails."""
    engine_mod._observability_sinks = lambda: (_Broken(), _Broken())
    engine = _engine_with_events([_Event("done", {})])

    produced = [event async for event in engine.run(_Session(), "hello")]

    assert len(produced) == 1
    import app.core.observability.api as obs_api

    obs_api._trace_collector = None
    obs_api._audit_chain = None


class _Broken:
    def start_span(self, *a, **k):
        raise RuntimeError("observability is down")

    def add_event(self, *a, **k):
        raise RuntimeError("observability is down")

    def end_span(self, *a, **k):
        raise RuntimeError("observability is down")

    def log_decision(self, *a, **k):
        raise RuntimeError("observability is down")


def test_emergency_stop_short_circuits_before_tracing(sinks):
    from app.core.observability import emergency_stop as es

    manager = es.EmergencyStopManager(db_path=":memory:")
    manager.activate(reason="test", triggered_by="tester")
    es.set_emergency_stop(manager)
    try:
        _, audit = sinks
        engine = _engine_with_events([_Event("done", {})])

        import asyncio

        events = asyncio.run(_drain(engine, _Session("s-stop"), "hello"))

        assert events[0].data.get("emergency_stop") is True
        assert audit.get_chain(limit=10) == [], "a refused run must not be audited as started"
    finally:
        es.set_emergency_stop(None)


async def _drain(engine, session, message):
    return [event async for event in engine.run(session, message)]


def test_api_sinks_are_the_shared_instances():
    assert get_trace_collector() is get_trace_collector()
    assert get_audit_chain() is get_audit_chain()


async def test_trace_api_reads_a_span_written_before_restart(tmp_path, monkeypatch):
    db_path = str(tmp_path / "trace-api.db")
    writer = TraceCollector(db_path=db_path)
    span = writer.start_span("restartable-operation", tags={"source": "test"})
    assert span is not None
    writer.end_span(span)

    reopened = TraceCollector(db_path=db_path)
    monkeypatch.setattr("app.core.observability.api._trace_collector", reopened)

    listing = await list_traces(limit=10, offset=0)
    detail = await get_trace(span.trace_id)

    assert listing["traces"][0]["trace_id"] == span.trace_id
    assert listing["traces"][0]["span_count"] == 1
    assert detail["span_count"] == 1
    assert detail["spans"][0]["operation"] == "restartable-operation"
    assert detail["spans"][0]["tags"] == {"source": "test"}


async def test_audit_api_reads_an_entry_written_before_restart(tmp_path, monkeypatch):
    db_path = str(tmp_path / "audit-api.db")
    writer = AuditChain(db_path=db_path)
    entry = writer.log_decision(
        "tool_call",
        input_summary="read config",
        output_summary="ok",
        session_id="api-restart-session",
    )

    reopened = AuditChain(db_path=db_path)
    monkeypatch.setattr("app.core.observability.api._audit_chain", reopened)

    response = await list_audit_entries(
        limit=10,
        offset=0,
        decision_type="tool_call",
        session_id=None,
    )

    assert response["total"] == 1
    assert response["entries"] == [entry.to_dict()]
