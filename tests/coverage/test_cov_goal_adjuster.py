"""Coverage tests for app.core.metacognition.goal_adjuster."""

from __future__ import annotations

import pytest

from app.core.metacognition.goal_adjuster import (
    AdjustmentResult,
    GoalAssessment,
    GoalDynamicAdjuster,
)


def test_feasible_when_no_failures_or_gaps() -> None:
    adj = GoalDynamicAdjuster()
    assessment = adj.assess_feasibility("write a function", ["read_file"], 0, [])
    assert assessment.feasible is True
    assert assessment.reason == "Goal appears feasible"
    assert assessment.suggested_goal == ""


def test_infeasible_after_too_many_failures() -> None:
    adj = GoalDynamicAdjuster()
    assessment = adj.assess_feasibility("do a and b and c", ["read_file"], 5, [])
    assert assessment.feasible is False
    assert "failed 5 times" in assessment.reason
    assert assessment.scope_reduction == 0.5
    assert assessment.suggested_goal == "do a"


def test_smaller_scope_comma_precedence() -> None:
    adj = GoalDynamicAdjuster()
    assessment = adj.assess_feasibility("first, second, third", [], 9, [])
    assert assessment.suggested_goal == "first"


def test_smaller_scope_long_goal_truncated() -> None:
    adj = GoalDynamicAdjuster()
    assessment = adj.assess_feasibility("one two three four five six seven eight", [], 6, [])
    assert assessment.suggested_goal == "one two three four five six"


def test_smaller_scope_short_goal_unchanged() -> None:
    adj = GoalDynamicAdjuster()
    assessment = adj.assess_feasibility("short goal", [], 6, [])
    assert assessment.suggested_goal == "short goal"


def test_capability_gap_database() -> None:
    adj = GoalDynamicAdjuster()
    assessment = adj.assess_feasibility("query the database for users", ["read_file"], 0, [])
    assert assessment.feasible is False
    assert "database_access" in assessment.prerequisites
    assert assessment.scope_reduction == 0.3
    assert assessment.suggested_goal == "query the database for users"


def test_capability_gap_database_with_run_command_adapts() -> None:
    adj = GoalDynamicAdjuster()
    assessment = adj.assess_feasibility("query the database", ["run_command"], 0, [])
    assert assessment.feasible is False
    assert "CLI database tools" in assessment.suggested_goal


def test_capability_gap_browser_adapts_with_web_search() -> None:
    adj = GoalDynamicAdjuster()
    assessment = adj.assess_feasibility("take a screenshot of the page", ["web_search"], 0, [])
    assert "browser_access" in assessment.prerequisites
    assert "using web search" in assessment.suggested_goal


def test_capability_gap_api_adapts_with_run_command() -> None:
    adj = GoalDynamicAdjuster()
    assessment = adj.assess_feasibility("make a rest api call", ["run_command"], 0, [])
    assert "api_access" in assessment.prerequisites
    assert "curl commands" in assessment.suggested_goal


def test_capability_gap_api_with_http_request_satisfied() -> None:
    adj = GoalDynamicAdjuster()
    assessment = adj.assess_feasibility("call an endpoint", ["http_request"], 0, [])
    assert assessment.feasible is True


def test_gap_not_adaptable_returns_original_goal() -> None:
    adj = GoalDynamicAdjuster()
    assessment = adj.assess_feasibility("scrape the web page", ["read_file"], 0, [])
    assert assessment.suggested_goal == "scrape the web page"


def test_broad_goal_feasible_decomposition() -> None:
    adj = GoalDynamicAdjuster()
    goal = (
        "refactor all the modules and update every test and document everything and "
        "add metrics and handle errors and improve logs and verify output and "
        "profile performance and review security and polish the ui and ship it"
    )
    assessment = adj.assess_feasibility(goal, ["read_file"], 0, [])
    assert assessment.feasible is True
    assert "broad" in assessment.reason


def test_broad_goal_with_comma_decomposes() -> None:
    adj = GoalDynamicAdjuster()
    goal = "do all of this, do that, and more, and more, and more, and more, and more"
    assessment = adj.assess_feasibility(goal, ["read_file"], 0, [])
    assert assessment.feasible is True
    assert assessment.suggested_goal.startswith("Focus on first part:")


def test_adjust_no_change_when_feasible() -> None:
    adj = GoalDynamicAdjuster()
    result = adj.adjust("simple task", ["read_file"], 0, [])
    assert result.adjusted is False
    assert result.revised == "simple task"
    assert result.alternatives == []
    assert adj._adjustment_history == []


def test_adjust_infeasible_generates_alternatives() -> None:
    adj = GoalDynamicAdjuster()
    result = adj.adjust("query the database", ["run_command", "read_file", "write_file"], 0, [])
    assert result.adjusted is True
    assert result.original == "query the database"
    assert result.revised != result.original
    assert any("CLI commands" in a for a in result.alternatives)
    assert any("Manual file editing" in a for a in result.alternatives)
    assert len(adj._adjustment_history) == 1


def test_adjust_stops_at_max_adjustments() -> None:
    adj = GoalDynamicAdjuster()
    for i in range(3):
        res = adj.adjust(f"query db {i}", ["run_command"], 0, [])
        assert res.adjusted is True
    capped = adj.adjust("query db another", ["run_command"], 0, [])
    assert capped.adjusted is False
    assert capped.reason == "Maximum adjustments reached. Stopping."
    assert capped.revised == "query db another"


def test_generate_alternatives_web_search_only() -> None:
    adj = GoalDynamicAdjuster()
    alts = adj._generate_alternatives("goal", ["web_search"])
    assert alts == ["Research-based approach for: goal"]


def test_generate_alternatives_empty_fallbacks() -> None:
    adj = GoalDynamicAdjuster()
    alts = adj._generate_alternatives("goal", ["unknown_tool"])
    assert alts == [
        "Break the goal into smaller sub-goals",
        "Request human assistance for unavailable capabilities",
    ]


def test_generate_alternatives_capped_at_three() -> None:
    adj = GoalDynamicAdjuster()
    alts = adj._generate_alternatives(
        "goal", ["run_command", "read_file", "write_file", "web_search"]
    )
    assert len(alts) == 3


def test_estimate_scope_scoring() -> None:
    adj = GoalDynamicAdjuster()
    assert adj._estimate_scope("short goal") == 0.0
    assert adj._estimate_scope(" ".join(["w"] * 21)) == 0.3
    assert adj._estimate_scope(" ".join(["w"] * 41)) == 0.5
    assert adj._estimate_scope("a, b") == 0.2
    assert adj._estimate_scope("do all the things") == 0.2
    assert adj._estimate_scope("a and b and c") == 0.2
    assert adj._estimate_scope("x, " + " ".join(["w"] * 41) + " and y") == pytest.approx(0.8)
    long_goal = " all " + " ".join(["w"] * 41) + ", a and b and c and d and e and f"
    assert adj._estimate_scope(long_goal) == 1.0


def test_decompose_goal_with_and_without_comma() -> None:
    adj = GoalDynamicAdjuster()
    assert adj._decompose_goal("a, b") == "Focus on first part: a"
    assert adj._decompose_goal("a b") == "a b"


def test_reset_clears_history() -> None:
    adj = GoalDynamicAdjuster()
    adj.adjust("query the database", ["run_command"], 0, [])
    assert adj._adjustment_history
    adj.reset()
    assert adj._adjustment_history == []


def test_dataclass_defaults() -> None:
    ga = GoalAssessment(feasible=True, reason="r", original_goal="g")
    assert ga.suggested_goal == ""
    assert ga.prerequisites == []
    ar = AdjustmentResult(adjusted=False, original="a", revised="a", reason="r")
    assert ar.alternatives == []
