"""HTTP-level coverage for the mounted ``/api/v1/reason`` router."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.reasoning import ReasoningMode, ReasoningResult
from tests.api.conftest import bearer

BASE = "/api/v1/reason"


class _UnavailableReasoning:
    def is_available(self) -> bool:
        return False


class _FakeReasoning:
    def __init__(self, result: ReasoningResult) -> None:
        self.pipeline = SimpleNamespace(reason=self._reason)
        self._result = result

    def is_available(self) -> bool:
        return True

    async def _reason(self, _request):
        return self._result


class _FakeEngine:
    def __init__(self, reasoning) -> None:
        self.reasoning = reasoning


def _result() -> ReasoningResult:
    return ReasoningResult(answer="fake answer", mode_used=ReasoningMode.AUTO)


async def test_modes_returns_documented_reasoning_modes(http) -> None:
    response = await http.get(f"{BASE}/modes")

    assert response.status_code == 200
    modes = response.json()
    assert {mode["id"] for mode in modes} == {"auto", "tree", "deep", "debate"}
    assert all(mode["available"] is True for mode in modes)


async def test_reason_requires_write_scope_when_auth_enabled(http, auth_on) -> None:
    response = await http.post(f"{BASE}/", json={"task": "classify"}, headers=bearer("reader", ["read"]))

    assert response.status_code == 403
    assert "write" in response.json()["detail"]


@pytest.mark.parametrize("path", [f"{BASE}/", BASE])
async def test_reason_rejects_invalid_request_body(http, path) -> None:
    response = await http.post(path, json={})

    assert response.status_code == 422
    assert response.json()["detail"]


async def test_reason_reports_unavailable_engine(http, monkeypatch) -> None:
    import app.core.reasoning.api as reasoning_api

    monkeypatch.setattr(reasoning_api, "get_engine", lambda: _FakeEngine(_UnavailableReasoning()))

    response = await http.post(f"{BASE}/", json={"task": "classify"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Reasoning engine not initialized"


async def test_reason_returns_result_fields_and_accepts_both_slash_forms(http, monkeypatch) -> None:
    import app.core.reasoning.api as reasoning_api

    monkeypatch.setattr(reasoning_api, "get_engine", lambda: _FakeEngine(_FakeReasoning(_result())))

    async def _ignore_trace(self, _values):
        return None

    monkeypatch.setattr(reasoning_api.ReasoningTraceRepository, "create", _ignore_trace)

    for path in (f"{BASE}/", BASE):
        response = await http.post(path, json={"task": "classify"})
        assert response.status_code == 200
        assert response.json()["answer"] == "fake answer"
        assert response.json()["mode_used"] == "auto"


async def test_reason_stream_reports_unavailable_engine(http, monkeypatch) -> None:
    import app.core.reasoning.api as reasoning_api

    monkeypatch.setattr(reasoning_api, "get_engine", lambda: _FakeEngine(_UnavailableReasoning()))

    response = await http.post(f"{BASE}/stream", json={"task": "classify"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Reasoning engine not initialized"


async def test_reason_trace_and_feedback_return_404_for_unknown_trace(http) -> None:
    trace = await http.get(f"{BASE}/missing-trace")
    feedback = await http.get(f"{BASE}/missing-trace/feedback")
    submit = await http.post(f"{BASE}/missing-trace/feedback", json={"rating": 1})

    assert trace.status_code == 200
    assert trace.json() is None
    assert feedback.status_code == 404
    assert feedback.json()["detail"] == "Trace not found"
    assert submit.status_code == 404
    assert submit.json()["detail"] == "Trace not found"


async def test_reason_history_returns_a_list(http) -> None:
    response = await http.get(f"{BASE}/history?limit=5")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
