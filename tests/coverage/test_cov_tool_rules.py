"""Coverage tests for app.core.engine.tool_rules."""

from __future__ import annotations

from app.core.engine.tool_rules import (
    HeartbeatController,
    RulesCheckResult,
    ToolCallRecord,
    ToolRule,
    ToolRulesSolver,
    ToolRuleType,
)


def test_register_and_recommend_with_no_rule_is_allowed() -> None:
    solver = ToolRulesSolver()
    assert solver.check_tool_call("unknown").allowed is True
    assert solver.get_recommended_next(["unknown", "other"]) == ["unknown", "other"]


def test_register_rules_bulk_and_overwrite() -> None:
    solver = ToolRulesSolver()
    solver.register_rules([ToolRule(tool_name="a"), ToolRule(tool_name="b")])
    solver.register_rule(ToolRule(tool_name="a", rule_type=ToolRuleType.TERMINAL))
    assert solver._rules["a"].rule_type is ToolRuleType.TERMINAL
    assert "b" in solver._rules


def test_terminal_rule_blocks_batching() -> None:
    solver = ToolRulesSolver()
    solver.register_rule(ToolRule(tool_name="finish", rule_type=ToolRuleType.TERMINAL))
    assert solver.check_tool_call("finish", batch=["finish"]).allowed is True
    result = solver.check_tool_call("finish", batch=["finish", "other"])
    assert result.allowed is False
    assert any("terminal" in r for r in result.violated_rules)


def test_init_rule_must_be_first() -> None:
    solver = ToolRulesSolver()
    solver.register_rule(ToolRule(tool_name="boot", rule_type=ToolRuleType.INIT))
    assert solver.check_tool_call("boot").allowed is True
    solver.record_result("boot", success=True)
    result = solver.check_tool_call("boot")
    assert result.allowed is False
    assert any("init tool" in r for r in result.violated_rules)


def test_continue_rule_needs_prior_call() -> None:
    solver = ToolRulesSolver()
    solver.register_rule(ToolRule(tool_name="next", rule_type=ToolRuleType.CONTINUE))
    blocked = solver.check_tool_call("next")
    assert blocked.allowed is False
    assert any("no prior tool calls" in r for r in blocked.violated_rules)
    solver.record_result("seed", success=True)
    assert solver.check_tool_call("next").allowed is True


def test_failure_retry_blocked_when_max_retries_zero() -> None:
    solver = ToolRulesSolver()
    solver.register_rule(ToolRule(tool_name="flaky", max_retries=0))
    solver.record_result("flaky", success=False, error="boom")
    result = solver.check_tool_call("flaky")
    assert result.allowed is False
    assert any("already failed" in r for r in result.violated_rules)


def test_failed_tool_with_retries_allowed() -> None:
    solver = ToolRulesSolver()
    solver.register_rule(ToolRule(tool_name="flaky", max_retries=2))
    solver.record_result("flaky", success=False, error="boom")
    assert solver.check_tool_call("flaky").allowed is True


def test_requires_constraint() -> None:
    solver = ToolRulesSolver()
    solver.register_rule(ToolRule(tool_name="write", requires=["read"]))
    blocked = solver.check_tool_call("write")
    assert blocked.allowed is False
    assert any("requires read" in r for r in blocked.violated_rules)
    solver.record_result("read", success=True)
    assert solver.check_tool_call("write").allowed is True


def test_excludes_constraint() -> None:
    solver = ToolRulesSolver()
    solver.register_rule(ToolRule(tool_name="a", excludes=["b"]))
    assert solver.check_tool_call("a", batch=["a", "b"]).allowed is False
    assert solver.check_tool_call("a", batch=["a"]).allowed is True
    assert solver.check_tool_call("a", batch=["a", "a"]).allowed is True


def test_multiple_violations_aggregate_and_reason() -> None:
    solver = ToolRulesSolver()
    solver.register_rule(
        ToolRule(tool_name="t", rule_type=ToolRuleType.TERMINAL, requires=["missing"])
    )
    result = solver.check_tool_call("t", batch=["t", "other"])
    assert result.allowed is False
    assert len(result.violated_rules) == 2
    assert result.reason == "Tool 't' violated 2 rule(s)"


def test_filter_batch_splits_allowed_and_rejected() -> None:
    solver = ToolRulesSolver()
    solver.register_rule(ToolRule(tool_name="finish", rule_type=ToolRuleType.TERMINAL))
    allowed, rejected = solver.filter_batch(["finish", "work"])
    assert allowed == ["work"]
    assert rejected == ["finish"]


def test_record_result_truncates_and_history_summary() -> None:
    solver = ToolRulesSolver()
    solver.record_result("a", success=True, result="x" * 500)
    solver.record_result("b", success=False, error="e")
    summary = solver.get_history_summary()
    assert summary["total_calls"] == 2
    assert summary["successful"] == 1
    assert summary["failed"] == 1
    assert summary["failed_tools"] == ["b"]
    assert summary["call_order"] == ["a", "b"]
    assert len(solver._call_history[0].result_summary) == 200


def test_record_result_empty_result_leaves_empty_summary() -> None:
    solver = ToolRulesSolver()
    solver.record_result("a", success=True)
    assert solver._call_history[0].result_summary == ""


def test_reset_turn_clears_state() -> None:
    solver = ToolRulesSolver()
    solver.record_result("a", success=False)
    solver.reset_turn()
    assert solver._call_history == []
    assert solver._failed_tools == set()
    assert solver._call_order == 0


def test_rules_check_result_defaults() -> None:
    r = RulesCheckResult(allowed=True)
    assert r.reason == ""
    assert r.violated_rules == []


def test_tool_call_record_defaults() -> None:
    rec = ToolCallRecord(tool_name="x")
    assert rec.success is True
    assert rec.arguments == {}
    assert rec.order == 0


def test_heartbeat_controller_lifecycle() -> None:
    hb = HeartbeatController(max_heartbeats=2)
    assert hb.remaining == 2
    assert hb.is_exhausted is False
    assert hb.record_heartbeat() is True
    assert hb.record_heartbeat() is True
    assert hb.record_heartbeat() is False
    assert hb.is_exhausted is True
    assert hb.remaining == 0
    hb.reset()
    assert hb.remaining == 2


def test_heartbeat_signal_detection() -> None:
    hb = HeartbeatController(max_heartbeats=1)
    assert hb.check_heartbeat_signal("no signal here") is True
    assert hb.check_heartbeat_signal("text <heartbeat> more") is True
    assert hb.check_heartbeat_signal("<heartbeat>") is False
    status = hb.get_status()
    assert status == {"count": 1, "max": 1, "remaining": 0, "exhausted": True}
