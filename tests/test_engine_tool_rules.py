"""Tests for tool rules solver."""


from app.core.engine.tool_rules import (
    HeartbeatController,
    ToolRule,
    ToolRulesSolver,
    ToolRuleType,
)


class TestToolRulesSolver:
    def test_register_rule(self) -> None:
        solver = ToolRulesSolver()
        solver.register_rule(ToolRule(tool_name="search", rule_type=ToolRuleType.NORMAL))
        assert "search" in solver._rules

    def test_normal_tool_always_allowed(self) -> None:
        solver = ToolRulesSolver()
        solver.register_rule(ToolRule(tool_name="search", rule_type=ToolRuleType.NORMAL))
        result = solver.check_tool_call("search")
        assert result.allowed is True

    def test_terminal_tool_rejects_batch(self) -> None:
        solver = ToolRulesSolver()
        solver.register_rule(ToolRule(tool_name="submit", rule_type=ToolRuleType.TERMINAL))
        result = solver.check_tool_call("submit", batch=["submit", "search"])
        assert result.allowed is False
        assert len(result.violated_rules) > 0

    def test_terminal_tool_allows_solo(self) -> None:
        solver = ToolRulesSolver()
        solver.register_rule(ToolRule(tool_name="submit", rule_type=ToolRuleType.TERMINAL))
        result = solver.check_tool_call("submit", batch=["submit"])
        assert result.allowed is True

    def test_init_tool_must_be_first(self) -> None:
        solver = ToolRulesSolver()
        solver.register_rule(ToolRule(tool_name="init", rule_type=ToolRuleType.INIT))
        solver.record_result("search", success=True)
        result = solver.check_tool_call("init")
        assert result.allowed is False

    def test_init_tool_first_call(self) -> None:
        solver = ToolRulesSolver()
        solver.register_rule(ToolRule(tool_name="init", rule_type=ToolRuleType.INIT))
        result = solver.check_tool_call("init")
        assert result.allowed is True

    def test_continue_tool_requires_prior(self) -> None:
        solver = ToolRulesSolver()
        solver.register_rule(ToolRule(tool_name="next_step", rule_type=ToolRuleType.CONTINUE))
        result = solver.check_tool_call("next_step")
        assert result.allowed is False

    def test_continue_tool_after_prior(self) -> None:
        solver = ToolRulesSolver()
        solver.register_rule(ToolRule(tool_name="next_step", rule_type=ToolRuleType.CONTINUE))
        solver.record_result("init", success=True)
        result = solver.check_tool_call("next_step")
        assert result.allowed is True

    def test_requires_constraint(self) -> None:
        solver = ToolRulesSolver()
        solver.register_rule(ToolRule(
            tool_name="deploy",
            rule_type=ToolRuleType.NORMAL,
            requires=["build"],
        ))
        result = solver.check_tool_call("deploy")
        assert result.allowed is False

        solver.record_result("build", success=True)
        result = solver.check_tool_call("deploy")
        assert result.allowed is True

    def test_excludes_constraint(self) -> None:
        solver = ToolRulesSolver()
        solver.register_rule(ToolRule(
            tool_name="fast_mode",
            rule_type=ToolRuleType.NORMAL,
            excludes=["slow_mode"],
        ))
        result = solver.check_tool_call("fast_mode", batch=["fast_mode", "slow_mode"])
        assert result.allowed is False

    def test_failure_retry_blocked(self) -> None:
        solver = ToolRulesSolver()
        solver.register_rule(ToolRule(tool_name="api_call", max_retries=0))
        solver.record_result("api_call", success=False, error="timeout")
        result = solver.check_tool_call("api_call")
        assert result.allowed is False

    def test_filter_batch(self) -> None:
        solver = ToolRulesSolver()
        solver.register_rule(ToolRule(tool_name="submit", rule_type=ToolRuleType.TERMINAL))
        allowed, rejected = solver.filter_batch(["submit", "search", "log"])
        assert "submit" in rejected
        assert "search" in allowed

    def test_get_recommended_next(self) -> None:
        solver = ToolRulesSolver()
        solver.register_rule(ToolRule(tool_name="init", rule_type=ToolRuleType.INIT))
        solver.register_rule(ToolRule(tool_name="next", rule_type=ToolRuleType.CONTINUE))
        recommended = solver.get_recommended_next(["init", "next"])
        assert "init" in recommended
        assert "next" not in recommended

    def test_reset_turn(self) -> None:
        solver = ToolRulesSolver()
        solver.record_result("search", success=True)
        assert len(solver._call_history) == 1
        solver.reset_turn()
        assert len(solver._call_history) == 0

    def test_get_history_summary(self) -> None:
        solver = ToolRulesSolver()
        solver.record_result("search", success=True)
        solver.record_result("api", success=False, error="fail")
        summary = solver.get_history_summary()
        assert summary["total_calls"] == 2
        assert summary["successful"] == 1
        assert summary["failed"] == 1
        assert "api" in summary["failed_tools"]


class TestHeartbeatController:
    def test_initial_state(self) -> None:
        hb = HeartbeatController(max_heartbeats=5)
        assert hb.remaining == 5
        assert hb.is_exhausted is False

    def test_record_heartbeat(self) -> None:
        hb = HeartbeatController(max_heartbeats=3)
        assert hb.record_heartbeat() is True
        assert hb.remaining == 2

    def test_exhaustion(self) -> None:
        hb = HeartbeatController(max_heartbeats=2)
        hb.record_heartbeat()
        hb.record_heartbeat()
        assert hb.is_exhausted is True
        assert hb.record_heartbeat() is False

    def test_check_heartbeat_signal(self) -> None:
        hb = HeartbeatController(max_heartbeats=3)
        assert hb.check_heartbeat_signal("working... <heartbeat>") is True
        assert hb._heartbeat_count == 1

    def test_non_heartbeat_signal(self) -> None:
        hb = HeartbeatController(max_heartbeats=3)
        assert hb.check_heartbeat_signal("normal output") is True
        assert hb._heartbeat_count == 0

    def test_reset(self) -> None:
        hb = HeartbeatController(max_heartbeats=3)
        hb.record_heartbeat()
        hb.record_heartbeat()
        hb.reset()
        assert hb.remaining == 3

    def test_get_status(self) -> None:
        hb = HeartbeatController(max_heartbeats=5)
        hb.record_heartbeat()
        status = hb.get_status()
        assert status["count"] == 1
        assert status["max"] == 5
        assert status["remaining"] == 4
        assert status["exhausted"] is False
