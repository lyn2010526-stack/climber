"""Coverage tests for app.core.reasoning.components.coverage."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from app.core.reasoning.base import Assumption, Candidate, EdgeCase
from app.core.reasoning.components.coverage import (
    _DEFAULT_CHECKLIST,
    CoverageChecker,
)


class _Response:
    def __init__(self, content: str) -> None:
        self.content = content


class _Adapter:
    provider = "fake"

    def __init__(self, content: str = "{}", *, delay: float = 0.0, raises: bool = False) -> None:
        self._content = content
        self._delay = delay
        self._raises = raises
        self.calls = 0

    async def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> _Response:
        self.calls += 1
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._raises:
            raise RuntimeError("llm-down")
        return _Response(self._content)


def _candidate(
    cid: str, content: str, strategy: str = "linear", confidence: float = 0.7
) -> Candidate:
    return Candidate(id=cid, content=content, strategy=strategy, confidence=confidence)


def _full_report_json() -> str:
    return json.dumps(
        {
            "edge_cases": [
                {
                    "description": "empty input handling",
                    "category": "empty_input",
                    "tested": False,
                    "result": "",
                }
            ],
            "risks": [
                {
                    "description": "db down",
                    "probability": "high",
                    "impact": "medium",
                    "mitigation": "retry",
                },
                {"description": "cache miss", "probability": "bogus", "impact": "bogus"},
            ],
            "assumptions": [
                {
                    "statement": "timeouts are configured properly",
                    "validated": False,
                    "evidence": "",
                }
            ],
            "blind_spots": ["no rollback plan", "no rollback plan", ""],
        }
    )


async def test_check_happy_path_code_task() -> None:
    checker = CoverageChecker()
    adapter = _Adapter(_full_report_json())
    candidates = [
        _candidate("c1", "we handle empty input handling properly with timeouts are configured")
    ]
    report = await checker.check("build feature", candidates, adapter, task_type="code")
    assert report.score > 0
    assert report.edge_cases
    assert report.risks
    assert report.assumptions
    assert report.blind_spots == ["no rollback plan"]
    assert set(report.checklist) == set(_code_checklist())


def _code_checklist() -> list[str]:
    from app.core.reasoning.components.coverage import _TASK_TYPE_CHECKLISTS

    return _TASK_TYPE_CHECKLISTS["code"]


async def test_check_default_checklist_and_empty_candidates() -> None:
    checker = CoverageChecker()
    adapter = _Adapter(
        json.dumps({"edge_cases": [], "risks": [], "assumptions": [], "blind_spots": []})
    )
    report = await checker.check("task", [], adapter, task_type="general")
    assert set(report.checklist) == set(_DEFAULT_CHECKLIST)
    assert report.score == 0.0
    assert report.edge_cases == []


async def test_check_timeout_returns_empty_report() -> None:
    checker = CoverageChecker()
    adapter = _Adapter(_full_report_json(), delay=0.2)
    candidates = [_candidate("c1", "correctness_verified completeness_checked")]
    report = await checker.check("task", candidates, adapter, task_type="general", timeout=0.01)
    # timeout is swallowed by _call_llm -> empty raw report
    assert report.edge_cases == []
    assert report.risks == []
    assert report.checklist["correctness_verified"] is True


async def test_check_llm_exception_produces_partial_report(monkeypatch) -> None:
    checker = CoverageChecker()
    adapter = _Adapter()

    async def boom(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("cannot call")

    monkeypatch.setattr(checker, "_call_llm", boom)
    candidates = [_candidate("c1", "contains correctness_verified keyword")]
    report = await checker.check("task", candidates, adapter, task_type="general")
    assert report.blind_spots == ["LLM coverage analysis unavailable"]
    assert report.edge_cases == []
    assert report.checklist["correctness_verified"] is True


async def test_check_adapter_without_provider_attribute(monkeypatch) -> None:
    checker = CoverageChecker()

    class _NoProvider:
        async def chat(self, messages, **kwargs):
            raise RuntimeError("fail")

    async def boom(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("fail")

    monkeypatch.setattr(checker, "_call_llm", boom)
    report = await checker.check("task", [], _NoProvider(), task_type="analysis")
    assert report.blind_spots


async def test_check_real_adapter_exception_is_swallowed() -> None:
    checker = CoverageChecker()
    adapter = _Adapter(raises=True)
    candidates = [_candidate("c1", "risks_identified completeness_checked")]
    report = await checker.check("task", candidates, adapter, task_type="general")
    assert adapter.calls == 1
    assert report.edge_cases == []
    assert report.checklist["completeness_checked"] is True


def test_extract_json_variants() -> None:
    checker = CoverageChecker()
    assert checker._extract_json('{"a": 1}') == {"a": 1}

    fenced = '```\n{"a": 2}\n```'
    assert checker._extract_json(fenced) == {"a": 2}

    fenced_no_close = '```\n{"a": 3}'
    assert checker._extract_json(fenced_no_close) == {"a": 3}

    json_prefixed = 'json {"a": 4}'
    assert checker._extract_json(json_prefixed) == {"a": 4}

    noisy = 'Here you go: {"a": 5} done'
    assert checker._extract_json(noisy) == {"a": 5}

    assert checker._extract_json("no json here") == {}


def test_parse_edge_cases_skips_invalid() -> None:
    checker = CoverageChecker()
    parsed = checker._parse_edge_cases(
        [
            {"description": "ok", "category": "cat", "tested": True, "result": "pass"},
            {"description": {"bad": "type"}, "category": "cat"},
        ]
    )
    assert len(parsed) == 1
    assert parsed[0].tested is True


def test_parse_risks_normalizes_levels() -> None:
    checker = CoverageChecker()
    parsed = checker._parse_risks(
        [
            {"description": "r1", "probability": "high", "impact": "medium"},
            {"description": "r2", "probability": "invalid", "impact": "invalid"},
            {"description": {"bad": 1}},
        ]
    )
    assert parsed[0].probability == "high"
    assert parsed[1].probability == "low"
    assert parsed[1].impact == "low"
    assert len(parsed) == 2


def test_parse_assumptions() -> None:
    checker = CoverageChecker()
    parsed = checker._parse_assumptions(
        [
            {"statement": "s1", "validated": True},
            {"statement": {"bad": 1}},
        ]
    )
    assert len(parsed) == 1 and parsed[0].validated is True


def test_parse_blind_spots_dedup_and_filter() -> None:
    checker = CoverageChecker()
    candidates = [_candidate("c1", "some unrelated discussion")]
    spots = checker._parse_blind_spots(
        ["  Rollback ", "rollback", "", "unique gap"],
        candidates,
    )
    assert spots == ["Rollback", "unique gap"]


def test_cross_reference_edge_cases_and_checklist() -> None:
    checker = CoverageChecker()
    ec = EdgeCase(description="timeout handling", category="misc")
    ec_unmatched = EdgeCase(description="zzzz", category="other")
    candidates = [_candidate("c1", "we improved timeout handling greatly")]
    checklist = {"timeout_handling": False, "misc": False, "unrelated": False}
    checker._cross_reference_edge_cases([ec, ec_unmatched], candidates, checklist)
    assert ec.tested is True
    assert ec.result == "addressed_in_output"
    assert ec_unmatched.tested is False
    assert checklist["misc"] is True
    assert checklist["unrelated"] is False


def test_cross_reference_assumptions() -> None:
    checker = CoverageChecker()
    assumption = Assumption(statement="network latency is negligible overall")
    unmatched = Assumption(statement="qqqq")
    candidates = [_candidate("c1", "we assume network latency is negligible for this system")]
    checker._cross_reference_assumptions([assumption, unmatched], candidates, {})
    assert assumption.validated is True
    assert assumption.evidence
    assert unmatched.validated is False


def test_compute_score_variants() -> None:
    checker = CoverageChecker()
    assert checker._compute_score({}, [], []) == 0.0

    # empty checklist but present edge cases (checklist_score stays 0)
    edge_only = checker._compute_score(
        {}, [EdgeCase(description="d", category="c", tested=True)], []
    )
    assert edge_only == 0.35

    score = checker._compute_score(
        {"a": True, "b": False},
        [EdgeCase(description="d", category="c", tested=True)],
        [Assumption(statement="s", validated=False)],
    )
    assert 0.0 < score < 1.0

    perfect = checker._compute_score(
        {"a": True},
        [EdgeCase(description="d", category="c", tested=True)],
        [Assumption(statement="s", validated=True)],
    )
    assert perfect == 1.0


def test_combine_candidates_skips_empty() -> None:
    checker = CoverageChecker()
    combined = checker._combine_candidates([_candidate("c1", "content"), _candidate("c2", "")])
    assert "c1" in combined
    assert "c2" not in combined


def test_build_prompt_includes_schema_and_candidates() -> None:
    checker = CoverageChecker()
    prompt = checker._build_prompt("my task", "combined", [_candidate("c1", "abc")])
    assert "my task" in prompt
    assert "edge_cases" in prompt
    assert "Candidate c1" in prompt
