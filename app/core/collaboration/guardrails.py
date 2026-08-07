"""Guardrail validation for group collaboration output."""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from app.core.collaboration.agent_runner import run_agent_simple
from app.core.collaboration.resolver import resolve_api_key, resolve_base_url
from app.core.group_ws_hub import group_ws_hub

logger = structlog.get_logger(__name__)


async def run_guardrails(task: Any, output: str) -> tuple[bool, list[dict[str, Any]]]:
    """Run guardrails on task output.

    Args:
        task: The task entity with guardrail configuration.
        output: The output text to validate.

    Returns:
        A tuple of (passed, feedback_issues).
    """
    if not task.guardrails:
        return True, []

    issues: list[dict[str, Any]] = []
    for guardrail in task.guardrails:
        g_type = guardrail.get("type", "llm")
        if g_type == "llm":
            passed, feedback = await run_llm_guardrail(task, output, guardrail)
            if not passed:
                issues.extend(feedback)
        elif g_type == "function":
            passed, feedback = await run_function_guardrail(output, guardrail)
            if not passed:
                issues.extend(feedback)
        elif g_type == "schema" and task.output_schema:
            passed, errors = validate_structured_output(output, task.output_schema)
            if not passed:
                issues.append({"description": "Schema validation failed", "severity": "high", "details": errors})

    await group_ws_hub.broadcast(task.group_id, {
        "type": "guardrail_check",
        "data": {"passed": len(issues) == 0, "issues_count": len(issues)},
    })

    return len(issues) == 0, issues


async def run_llm_guardrail(
    task: Any,
    output: str,
    guardrail: dict[str, Any],
) -> tuple[bool, list[dict[str, Any]]]:
    """Run an LLM-based guardrail check.

    Args:
        task: The task entity for context.
        output: The output to validate.
        guardrail: The guardrail configuration.

    Returns:
        A tuple of (passed, issues).
    """
    from app.core.collaboration.constants import TASK_TIMEOUT

    prompt = guardrail.get("validation_prompt") or f"""Review the following output against these requirements:
{guardrail.get('description', '')}

Output:
{output}

Respond with:
1. "通过" if the output meets all requirements, or "不通过" if not.
2. If not passing, list specific issues found."""

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
        logger.error("llm_guardrail_failed", task_id=task.id, error=str(e))
        return True, []

    lower_output = review_output.lower()
    passed = any(k in lower_output for k in ["通过", "pass", "approved", "looks good", "accept"])
    issues = _parse_issues(review_output) if not passed else []

    await group_ws_hub.broadcast(task.group_id, {
        "type": "guardrail_passed" if passed else "guardrail_failed",
        "data": {"guardrail_name": guardrail.get("name", "unnamed"), "passed": passed},
    })

    return passed, issues


async def run_function_guardrail(
    output: str,
    guardrail: dict[str, Any],
) -> tuple[bool, list[dict[str, Any]]]:
    """Run a function-based guardrail.

    Args:
        output: The output to validate.
        guardrail: The guardrail configuration with validation_function.

    Returns:
        A tuple of (passed, issues).
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
        if isinstance(result, bool):
            return result, []
        if isinstance(result, tuple):
            return result
        return True, []
    except Exception as e:
        logger.error("function_guardrail_failed", func_path=func_path, error=str(e))
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
        if line and any(k in line.lower() for k in ["issue", "问题", "error", "missing", "缺少", "错误", "incorrect"]):
            issues.append({"description": line, "severity": "medium"})
    return issues
