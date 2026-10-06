"""Execution-chain wiring tests: goal validation and prompt injection.

The task-worker handlers are the single funnel through which background tasks
reach a model, so the main-goal check and the mandatory core prompt must both
happen there — not merely exist as unused services.
"""

from __future__ import annotations

from app.core.task_worker import _check_objective, _injected_system_prompt


class TestGoalValidation:
    def test_blocked_objective_names_the_plain_language_reason(self) -> None:
        check = _check_objective("继续")
        assert check["status"] == "blocked"
        assert check["goal_preserved"] is False
        assert "目标" in check["plain_reason"]

    def test_clear_objective_is_ready(self) -> None:
        check = _check_objective("实现用户导出功能，输出 CSV")
        assert check["status"] == "ready"
        assert check["goal_preserved"] is True
        assert check["plain_reason"] is None

    def test_needs_clarification_still_runs(self) -> None:
        # "把这句话翻译成英文" has a goal but an unresolved reference; the run
        # proceeds because the caller's objective is authoritative.
        check = _check_objective("把这句话翻译成英文")
        assert check["status"] == "needs_clarification"
        assert check["goal_preserved"] is True

    def test_validator_crash_never_blocks_a_run(self) -> None:
        import app.core.observability.alignment as alignment

        original = alignment.validate_instruction_goal

        def boom(*args, **kwargs):
            raise RuntimeError("validation exploded")

        alignment.validate_instruction_goal = boom
        try:
            check = _check_objective("实现导出")
        finally:
            alignment.validate_instruction_goal = original
        assert check["status"] == "ready"


class TestPromptInjection:
    def test_explicit_caller_prompt_is_honoured(self) -> None:
        # Factory planner passes its own JSON-only prompt; injection must not
        # override it.
        payload = {"system_prompt": "Return JSON only."}
        assert _injected_system_prompt(payload) == "Return JSON only."

    def test_no_prompt_gets_the_active_core_prompt(self) -> None:
        injected = _injected_system_prompt({})
        assert injected, "core prompt must be injected when caller passes none"
        assert "core.system" not in injected  # the id is metadata, not body text

    def test_registry_failure_degrades_to_empty_prompt(self) -> None:
        import app.core.prompts as prompts_module

        original = prompts_module.build_injected_prompt

        def boom(*args, **kwargs):
            raise RuntimeError("registry unavailable")

        prompts_module.build_injected_prompt = boom
        try:
            assert _injected_system_prompt({}) == ""
        finally:
            prompts_module.build_injected_prompt = original
