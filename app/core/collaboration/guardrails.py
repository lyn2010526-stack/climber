"""Guardrail validation for group collaboration output.

Validator exceptions fail closed for both LLM and function guardrails: a
raised exception returns (False, [issue]) with an exception-category issue
carrying the error reason, instead of the previous fail-open behavior.
"""

from __future__ import annotations

import asyncio
from enum import StrEnum
from typing import Any

import structlog

from app.core.collaboration.agent_runner import run_agent_simple
from app.core.collaboration.resolver import resolve_api_key, resolve_base_url
from app.core.group_ws_hub import group_ws_hub

logger = structlog.get_logger(__name__)

CATEGORY_VALIDATION = "validation"
CATEGORY_EXCEPTION = "exception"


class GuardrailAction(StrEnum):
    """On-fail actions, mirroring guardrails-ai FailResult handling (Filter/Refrain).

    - REFRAIN: block the output when validation fails (default, current behavior).
    - FILTER: record the issue as feedback without blocking the output.
    - ALLOW: record the issue but treat the output as passing.
    """

    ALLOW = "allow"
    FILTER = "filter"
    REFRAIN = "refrain"


def _resolve_action(guardrail: dict[str, Any]) -> GuardrailAction:
    """Resolve the on-fail action from guardrail config, defaulting to REFRAIN.

    Args:
        guardrail: The guardrail configuration.

    Returns:
        The parsed GuardrailAction; unknown or missing values fall back to REFRAIN.
    """
    raw = str(guardrail.get("on_fail", "")).lower()
    for action in GuardrailAction:
        if raw == action.value:
            return action
    return GuardrailAction.REFRAIN


def _tag_issues(feedback: list[dict[str, Any]], action: GuardrailAction) -> list[dict[str, Any]]:
    """Copy feedback entries and tag them with category and on-fail action.

    Args:
        feedback: The raw issue entries produced by a validator.
        action: The on-fail action resolved from guardrail config.

    Returns:
        A list of tagged issue dictionaries.
    """
    tagged = []
    for issue in feedback:
        entry = dict(issue)
        entry.setdefault("category", CATEGORY_VALIDATION)
        entry.setdefault("action", action.value)
        tagged.append(entry)
    return tagged


def _exception_issue(description: str, error: Exception) -> dict[str, Any]:
    """Build an issue entry for a validator exception (blocking under strict).

    Args:
        description: Human-readable description of what raised.
        error: The caught exception.

    Returns:
        An issue dictionary with category "exception" and refrain action.
    """
    return {
        "description": f"{description}: {error}",
        "severity": "high",
        "category": CATEGORY_EXCEPTION,
        "action": GuardrailAction.REFRAIN.value,
        "details": str(error),
    }


async def run_guardrails(
    task: Any,
    output: str,
    strict: bool = False,
) -> tuple[bool, list[dict[str, Any]]]:
    """Run guardrails on task output.

    Args:
        task: The task entity with guardrail configuration.
        output: The output text to validate.
        strict: Retained for API compatibility; validator exceptions always
            fail closed with an issue of category "exception".

    Returns:
        A tuple of (passed, feedback_issues). Each issue carries "category"
        ("validation" or "exception") and "action" ("refrain" issues block the
        output, "filter"/"allow" issues are advisory only).
    """
    if not task.guardrails:
        return True, []

    issues: list[dict[str, Any]] = []
    for guardrail in task.guardrails:
        g_type = guardrail.get("type", "llm")
        if g_type == "llm":
            action = _resolve_action(guardrail)
            passed, feedback = await run_llm_guardrail(task, output, guardrail, strict=strict)
        elif g_type == "function":
            action = _resolve_action(guardrail)
            passed, feedback = await run_function_guardrail(output, guardrail, strict=strict)
        elif g_type == "schema" and task.output_schema:
            action = GuardrailAction.REFRAIN
            passed, errors = validate_structured_output(output, task.output_schema)
            feedback = (
                []
                if passed
                else [
                    {
                        "description": "Schema validation failed",
                        "severity": "high",
                        "details": errors,
                    }
                ]
            )
        else:
            continue

        if passed:
            continue
        if not feedback:
            feedback = [
                {
                    "description": (
                        f"Guardrail '{guardrail.get('name', 'unnamed')}' "
                        "reported failure without details"
                    ),
                    "severity": "medium",
                }
            ]
        issues.extend(_tag_issues(feedback, action))

    passed = all(
        issue.get("action", GuardrailAction.REFRAIN.value) != GuardrailAction.REFRAIN.value
        for issue in issues
    )

    await group_ws_hub.broadcast(
        task.group_id,
        {
            "type": "guardrail_check",
            "data": {"passed": passed, "issues_count": len(issues)},
        },
    )

    return passed, issues


async def run_llm_guardrail(
    task: Any,
    output: str,
    guardrail: dict[str, Any],
    strict: bool = False,
) -> tuple[bool, list[dict[str, Any]]]:
    """Run an LLM-based guardrail check.

    Args:
        task: The task entity for context.
        output: The output to validate.
        guardrail: The guardrail configuration.
        strict: Retained for API compatibility; validator exceptions always
            fail closed.

    Returns:
        A tuple of (passed, issues). Validator exceptions fail closed with an
        exception-category issue.
    """
    from app.core.collaboration.constants import TASK_TIMEOUT

    prompt = (
        guardrail.get("validation_prompt")
        or f"""Review the following output against these requirements:
{guardrail.get("description", "")}

Output:
{output}

Respond with:
1. "通过" if the output meets all requirements, or "不通过" if not.
2. If not passing, list specific issues found."""
    )

    review_output = ""
    try:
        async with __import__("asyncio").timeout(TASK_TIMEOUT):
            review_output, _ = await run_agent_simple(
                agent_id="guardrail-validator",
                provider="openai",
                model_id="gpt-4o",
                api_key=resolve_api_key("openai", ""),
                base_url=resolve_base_url("openai", None),
                system_prompt="You are a strict quality validator.",
                user_message=prompt,
                tools=[],
            )
    except Exception as e:
        logger.exception("llm_guardrail_failed", task_id=task.id, error=str(e), strict=strict)
        return False, [_exception_issue("LLM guardrail validator raised", e)]

    lower_output = review_output.lower()
    passed = any(k in lower_output for k in ["通过", "pass", "approved", "looks good", "accept"])
    issues = _parse_issues(review_output) if not passed else []

    await group_ws_hub.broadcast(
        task.group_id,
        {
            "type": "guardrail_passed" if passed else "guardrail_failed",
            "data": {"guardrail_name": guardrail.get("name", "unnamed"), "passed": passed},
        },
    )

    return passed, issues


async def run_function_guardrail(
    output: str,
    guardrail: dict[str, Any],
    strict: bool = False,
) -> tuple[bool, list[dict[str, Any]]]:
    """Run a function-based guardrail.

    Args:
        output: The output to validate.
        guardrail: The guardrail configuration with validation_function.
        strict: Retained for API compatibility; validator exceptions always
            fail closed.

    Returns:
        A tuple of (passed, issues). Validator exceptions fail closed with an
        exception-category issue instead of passing the output through.
    """
    import importlib

    func_path = guardrail.get("validation_function")
    if not func_path:
        return True, []

    try:
        module_path, func_name = func_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        fn = getattr(module, func_name)
        result = fn(output)
        if asyncio.iscoroutinefunction(fn):
            result = await result
    except Exception as e:
        logger.exception(
            "function_guardrail_failed", func_path=func_path, error=str(e), strict=strict
        )
        return False, [_exception_issue(f"Function guardrail '{func_path}' raised", e)]

    if isinstance(result, bool):
        return result, []
    if isinstance(result, tuple):
        return result
    return True, []


def validate_structured_output(output: str, schema: dict[str, Any]) -> tuple[bool, Any]:
    """Validate output against JSON schema.

    Args:
        output: The output text to validate.
        schema: The JSON schema to validate against.

    Returns:
        A tuple of (valid, parsed_or_errors).
    """
    from app.core.json_schema import validate_structured_output

    valid, parsed, errors = validate_structured_output(output, schema)
    if not valid:
        return False, {"errors": errors[:10], "raw": output[:500]}
    return True, parsed


def _parse_issues(review_output: str) -> list[dict[str, Any]]:
    """Extract issues from reviewer output.

    Args:
        review_output: The reviewer's output text.

    Returns:
        A list of issue dictionaries with description and severity.
    """
    issues = []
    lines = review_output.splitlines()
    for line in lines:
        line = line.strip()
        if line and any(
            k in line.lower()
            for k in ["issue", "问题", "error", "missing", "缺少", "错误", "incorrect"]
        ):
            issues.append({"description": line, "severity": "medium"})
    return issues
