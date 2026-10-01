"""Tests for guardrail validation.

Covers the default fail-open behavior (validator exceptions never block),
the strict fail-closed mode (exceptions block with an exception-category
issue carrying the error reason), and the GuardrailAction on-fail enum
(refrain blocks, filter/allow only record feedback).

Run with pytest; run_agent_simple, credential resolution and the websocket
broadcast are mocked. No live LLM.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.collaboration import guardrails
from app.core.collaboration.guardrails import (
    CATEGORY_EXCEPTION,
    CATEGORY_VALIDATION,
    GuardrailAction,
    run_guardrails,
)


def _sync_boom(_output: str) -> bool:
    raise RuntimeError("boom")


async def _async_boom(_output: str) -> bool:
    raise RuntimeError("async boom")


def _sync_true(_output: str) -> bool:
    return True


def _sync_false_bare(_output: str) -> bool:
    return False


def _sync_false_with_feedback(_output: str) -> tuple[bool, list[dict]]:
    return False, [{"description": "bad output detected", "severity": "high"}]


def test_action_enum_members():
    assert [action.value for action in GuardrailAction] == ["allow", "filter", "refrain"]


class GuardrailsRunTests(unittest.IsolatedAsyncioTestCase):
    def _task(self, guardrail_config: list[dict]) -> SimpleNamespace:
        return SimpleNamespace(
            id="task-1",
            group_id="group-1",
            guardrails=guardrail_config,
            output_schema=None,
        )

    async def asyncSetUp(self):
        self.broadcast = AsyncMock()
        broadcast_patcher = patch.object(guardrails.group_ws_hub, "broadcast", self.broadcast)
        broadcast_patcher.start()
        self.addCleanup(broadcast_patcher.stop)

        api_key_patcher = patch.object(guardrails, "resolve_api_key", return_value="key")
        base_url_patcher = patch.object(guardrails, "resolve_base_url", return_value=None)
        api_key_patcher.start()
        base_url_patcher.start()
        self.addCleanup(api_key_patcher.stop)
        self.addCleanup(base_url_patcher.stop)

    async def _run_llm(self, review_output: str, **kwargs) -> tuple[bool, list[dict]]:
        task = self._task([{"type": "llm", "name": "review"}])
        with patch.object(
            guardrails,
            "run_agent_simple",
            new_callable=AsyncMock,
            return_value=(review_output, []),
        ):
            return await run_guardrails(task, "worker output", **kwargs)

    def _function_task(self, function_name: str, on_fail: str | None = None) -> SimpleNamespace:
        config: dict = {
            "type": "function",
            "name": "fn-check",
            "validation_function": f"{__name__}.{function_name}",
        }
        if on_fail:
            config["on_fail"] = on_fail
        return self._task([config])

    async def test_no_guardrails_passthrough(self):
        passed, issues = await run_guardrails(self._task([]), "output")
        assert passed is True
        assert issues == []
        self.broadcast.assert_not_awaited()

    async def test_llm_pass_path_unaffected(self):
        passed, issues = await self._run_llm("approved, looks good")
        assert passed is True
        assert issues == []
        assert self.broadcast.await_count == 2
        check = self.broadcast.call_args_list[-1].args[1]
        assert check["type"] == "guardrail_check"
        assert check["data"]["passed"] is True

    async def test_llm_failure_default_refrain_blocks(self):
        passed, issues = await self._run_llm("Errors found: missing field X. 问题: incomplete")
        assert passed is False
        assert issues
        assert issues[0]["action"] == GuardrailAction.REFRAIN.value
        assert issues[0]["category"] == CATEGORY_VALIDATION

    async def test_llm_exception_default_fail_open(self):
        task = self._task([{"type": "llm", "name": "review"}])
        with patch.object(
            guardrails, "run_agent_simple", new_callable=AsyncMock, side_effect=RuntimeError("boom")
        ):
            passed, issues = await run_guardrails(task, "worker output")
        assert passed is True
        assert issues == []

    async def test_llm_exception_strict_fail_closed(self):
        task = self._task([{"type": "llm", "name": "review"}])
        with patch.object(
            guardrails, "run_agent_simple", new_callable=AsyncMock, side_effect=RuntimeError("boom")
        ):
            passed, issues = await run_guardrails(task, "worker output", strict=True)
        assert passed is False
        assert len(issues) == 1
        assert issues[0]["category"] == CATEGORY_EXCEPTION
        assert issues[0]["action"] == GuardrailAction.REFRAIN.value
        assert "boom" in issues[0]["description"]
        assert issues[0]["details"] == "boom"

    async def test_strict_no_exception_unaffected(self):
        passed, issues = await self._run_llm("approved, looks good", strict=True)
        assert passed is True
        assert issues == []

    async def test_function_exception_default_fail_open(self):
        task = self._function_task("_sync_boom")
        passed, issues = await run_guardrails(task, "output")
        assert passed is True
        assert issues == []

    async def test_function_exception_strict_fail_closed(self):
        task = self._function_task("_sync_boom")
        passed, issues = await run_guardrails(task, "output", strict=True)
        assert passed is False
        assert len(issues) == 1
        assert issues[0]["category"] == CATEGORY_EXCEPTION
        assert issues[0]["action"] == GuardrailAction.REFRAIN.value
        assert "boom" in issues[0]["description"]
        assert "_sync_boom" in issues[0]["description"]

    async def test_function_async_exception_strict_fail_closed(self):
        task = self._function_task("_async_boom")
        passed, issues = await run_guardrails(task, "output", strict=True)
        assert passed is False
        assert issues[0]["category"] == CATEGORY_EXCEPTION
        assert "async boom" in issues[0]["details"]

    async def test_function_false_without_feedback_blocks_by_default(self):
        task = self._function_task("_sync_false_bare")
        passed, issues = await run_guardrails(task, "output")
        assert passed is False
        assert len(issues) == 1
        assert issues[0]["action"] == GuardrailAction.REFRAIN.value
        assert issues[0]["category"] == CATEGORY_VALIDATION

    async def test_action_filter_records_without_blocking(self):
        task = self._function_task(
            "_sync_false_with_feedback", on_fail=GuardrailAction.FILTER.value
        )
        passed, issues = await run_guardrails(task, "output")
        assert passed is True
        assert len(issues) == 1
        assert issues[0]["action"] == GuardrailAction.FILTER.value
        assert issues[0]["category"] == CATEGORY_VALIDATION
        assert issues[0]["description"] == "bad output detected"

    async def test_action_allow_passes_through(self):
        task = self._function_task("_sync_false_bare", on_fail=GuardrailAction.ALLOW.value)
        passed, issues = await run_guardrails(task, "output")
        assert passed is True
        assert issues[0]["action"] == GuardrailAction.ALLOW.value

    async def test_action_refrain_explicit_blocks(self):
        task = self._function_task(
            "_sync_false_with_feedback", on_fail=GuardrailAction.REFRAIN.value
        )
        passed, issues = await run_guardrails(task, "output")
        assert passed is False
        assert issues[0]["action"] == GuardrailAction.REFRAIN.value

    async def test_action_filter_passing_function_has_no_issues(self):
        task = self._function_task("_sync_true", on_fail=GuardrailAction.FILTER.value)
        passed, issues = await run_guardrails(task, "output")
        assert passed is True
        assert issues == []


if __name__ == "__main__":
    unittest.main()
