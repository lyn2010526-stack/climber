"""Tests for tool prioritizer."""

from __future__ import annotations

import pytest

from app.core.tool_prioritizer import ToolPrioritizer, _jaccard, _tokenize


def test_tokenize():
    assert _tokenize("Read a file from disk") == {"read", "a", "file", "from", "disk"}


def test_jaccard():
    assert _jaccard({"a", "b"}, {"a", "c"}) == pytest.approx(1 / 3)
    assert _jaccard(set(), set()) == 0.0


def test_rank_tools_basic():
    p = ToolPrioritizer()
    tools = [
        {"type": "function", "function": {"name": "read_file", "description": "Read a file from the local filesystem"}},
        {"type": "function", "function": {"name": "web_search", "description": "Search the web using DuckDuckGo lite"}},
        {"type": "function", "function": {"name": "get_weather", "description": "Get current weather for a city"}},
    ]
    ranked = p.rank_tools("read the configuration file from disk", tools)
    assert ranked[0] == "read_file"


def test_rank_tools_learns_from_success():
    p = ToolPrioritizer()
    tools = [
        {"type": "function", "function": {"name": "web_search", "description": "Search the web using DuckDuckGo lite"}},
        {"type": "function", "function": {"name": "fetch_url", "description": "Fetch content from a URL"}},
    ]
    p.rank_tools("search the web for latest news", tools)
    # Record many successes for web_search
    for _ in range(10):
        p.record_outcome("web_search", True, 200.0)
    # Record failures for fetch_url
    for _ in range(10):
        p.record_outcome("fetch_url", False, 800.0)
    ranked = p.rank_tools("search the web for latest news", tools)
    assert ranked[0] == "web_search"


def test_record_outcome_updates_stats():
    p = ToolPrioritizer()
    p.record_outcome("run_command", True, 100.0)
    p.record_outcome("run_command", False, 300.0)
    stats = p.get_stats("run_command")
    assert stats["attempts"] == 2
    assert stats["success_rate"] == pytest.approx(0.5)
    assert stats["avg_duration_ms"] == pytest.approx(200.0)


def test_get_stats_defaults():
    p = ToolPrioritizer()
    stats = p.get_stats("unknown_tool")
    assert stats["attempts"] == 0
    assert stats["success_rate"] is None
    assert stats["avg_duration_ms"] is None
