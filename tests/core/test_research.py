"""Tests for the zero-key research pipeline."""

from __future__ import annotations

import pytest

from app.tools import research

_FIXED_HTML = """
<html>
<head><title>Pytest Testing Guide</title></head>
<body>
<h1>Pytest Installation and Setup</h1>
<p>Pytest is a battle-tested testing framework for Python. It makes it easy to
write simple and scalable test cases, from unit tests to complex functional
tests. Install pytest with pip and add the tests directory to the project.</p>
<ul>
    <li><a href="https://example.com/pytest-guide">pytest guide</a></li>
    <li><a href="https://example.com/testing-pitfalls">testing pitfalls</a></li>
    <li><a href="https://example.com/python-testing">python testing</a></li>
</ul>
<p>Common testing pitfalls include mutable shared state across tests, relying
on execution order, and slow fixtures. Using pytest fixtures keeps tests
isolated and deterministic.</p>
</body>
</html>
"""


@pytest.fixture(name="offline_browser")
def offline_browser(monkeypatch):
    monkeypatch.setattr(research, "_browser_available", lambda: False)


def test_run_research_returns_full_structure(monkeypatch, offline_browser) -> None:
    monkeypatch.setattr(
        research, "_fetch_url_sync", lambda url, timeout_s: _FIXED_HTML
    )
    result = research.run_research("pytest testing pitfalls", sources=3, timeout_s=5)

    assert result["ok"] is True
    assert result["query"] == "pytest testing pitfalls"
    assert isinstance(result["summary"], str) and result["summary"]
    assert isinstance(result["findings"], list) and result["findings"]
    assert isinstance(result["sources"], list) and result["sources"]
    assert result["generated_at"]

    for finding in result["findings"]:
        assert finding["source"].startswith("http")
        assert finding["title"]
        assert isinstance(finding["key_points"], list) and finding["key_points"]
        assert isinstance(finding["rel_score"], (int, float))

    assert result["sources"] == [f["source"] for f in result["findings"]]


def test_run_research_respects_sources_limit(monkeypatch, offline_browser) -> None:
    monkeypatch.setattr(
        research, "_fetch_url_sync", lambda url, timeout_s: _FIXED_HTML
    )
    result = research.run_research("pytest testing pitfalls", sources=2, timeout_s=5)

    assert result["ok"] is True
    assert len(result["findings"]) <= 2
    assert len(result["sources"]) <= 2


def test_run_research_all_sources_fail_returns_ok_false(monkeypatch, offline_browser) -> None:
    def _boom(url: str, timeout_s: int) -> str:
        raise OSError("simulated network failure")

    monkeypatch.setattr(research, "_fetch_url_sync", _boom)

    result = research.run_research("pytest testing pitfalls", sources=2, timeout_s=3)

    assert result["ok"] is False
    assert result["findings"] == []
    assert result["sources"] == []
    assert "no sources" in result["summary"].lower()


def test_run_research_never_raises_when_candidates_fail(monkeypatch, offline_browser) -> None:
    def _boom(url: str, timeout_s: int) -> str:
        raise RuntimeError("unexpected failure")

    monkeypatch.setattr(research, "_fetch_url_sync", _boom)

    result = research.run_research("anything", sources=1, timeout_s=3)

    assert result["ok"] is False
    assert not result["findings"]


def test_report_text_renders_with_title(monkeypatch, offline_browser) -> None:
    monkeypatch.setattr(
        research, "_fetch_url_sync", lambda url, timeout_s: _FIXED_HTML
    )
    result = research.run_research("pytest testing pitfalls", sources=2, timeout_s=5)
    report = research.research_report_text(result)

    assert report.startswith("# 调研报告：")
    assert "## 摘要" in report
    assert "## 调研发现" in report
    assert "## 来源列表" in report
    assert result["query"] in report
    assert "http" in report


def test_report_text_renders_for_failed_result() -> None:
    result = {
        "ok": False,
        "query": "nothing",
        "summary": "no sources reachable",
        "findings": [],
        "sources": [],
        "generated_at": "2026-01-01T00:00:00+00:00",
    }
    report = research.research_report_text(result)

    assert report.startswith("# 调研报告：")
    assert "no sources reachable" in report
