"""Tool execution and permission handling for the agent engine.

Extracted from ``app.core.agent_engine``. Validation always routes through
``engine._validate_tool_call`` so the facade override point cannot be
bypassed; persistence routes through ``engine._persist_message``.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from app.core import AgentEvent, AgentEventType, MessageRole
from app.core.engine.validation import _approval_key


def parse_tool_arguments(function: dict[str, Any]) -> dict[str, Any]:
    """Parse the arguments field of a tool call function.

    Args:
        function: The function dict from a tool call.

    Returns:
        A dictionary of parsed arguments (empty dict when unparseable or when
        the payload is not a JSON object). Non-object payloads (lists, scalars)
        are rejected here so downstream permission and schema checks, which
        assume a mapping, cannot be bypassed or crash the whole round.
    """
    arguments = function.get("arguments", {})
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = {}
    if not isinstance(arguments, dict):
        return {}
    return arguments


def request_permission(session: Any, event_data: dict[str, Any]) -> None:
    """Register the pending permission request on the session.

    Args:
        session: The current agent session.
        event_data: The TOOL_CALL event data carrying the request details.
    """
    session._pending_permission = {**event_data, "decision": None}
    session._permission_event = asyncio.Event()


async def wait_for_permission(session: Any, timeout_seconds: float) -> bool:
    """Wait for a permission decision on the session's pending request.

    Args:
        session: The current agent session with a pending permission event.
        timeout_seconds: Maximum time to wait for the decision.

    Returns:
        True when the request timed out, False when a decision arrived.
    """
    timed_out = False
    try:
        await asyncio.wait_for(session._permission_event.wait(), timeout=timeout_seconds)
    except TimeoutError:
        timed_out = True
        session._pending_permission["decision"] = "timeout"
    return timed_out


def resolve_permission_decision(
    session: Any,
    tool_name: str,
    arguments: dict[str, Any],
    timed_out: bool,
) -> bool:
    """Resolve the permission decision after waiting.

    Marks the call as approved for the rest of the session when the user
    allowed it; timeouts and denials leave the approval set untouched.

    Args:
        session: The current agent session.
        tool_name: The tool function name.
        arguments: The tool call arguments.
        timed_out: Whether the permission request timed out.

    Returns:
        True when the call was approved, False otherwise.
    """
    decision = session._pending_permission.get("decision") if session._pending_permission else None
    session._pending_permission = None
    session._permission_event = None
    if timed_out or decision not in {"allow", "allow_session", "allow_always"}:
        return False
    approved = getattr(session, "_approved_tool_calls", None)
    if approved is None:
        approved = set()
        session._approved_tool_calls = approved
    approved.add(_approval_key(tool_name, arguments))
    return True


async def persist_tool_result(engine: Any, session: Any, tr: Any) -> None:
    """Append a tool result message to the session and persist it.

    Args:
        engine: The AgentEngine instance (persistence override point).
        session: The current agent session.
        tr: The tool execution result.
    """
    content = tr.result or tr.error or ""
    session.messages.append({"role": MessageRole.TOOL, "content": content, "tool_call_id": tr.tool_call_id or tr.tool_name})
    persisted = await engine._persist_message(
        session.session_id,
        MessageRole.TOOL,
        content=content,
        tool_name=tr.tool_name,
        tool_call_id=tr.tool_call_id,
    )
    if getattr(session, "_continuing_input", False) and not persisted:
        raise RuntimeError("Follow-up tool result persistence failed")


async def handle_tool_debug(engine: Any, session: Any, tr: Any) -> None:
    """Handle debug recovery for failed tool calls.

    Uses the engine's tool registry for retry callbacks; sessions never
    carry a registry themselves.

    Args:
        engine: The AgentEngine instance providing ``debug_loop`` and the
            tool registry.
        session: The current agent session.
        tr: The tool result to check for errors.
    """
    if engine.debug_loop and tr.error:
        key = tr.tool_name
        attempts = session.debug_attempts.get(key, 0)
        if attempts < 3:
            session.debug_attempts[key] = attempts + 1
            fixed = await engine.debug_loop.recover(
                tool_name=tr.tool_name,
                arguments=tr.arguments or {},
                error_output=tr.error or tr.result,
                retry_callback=lambda retry_tool, retry_args: engine.tool_registry.execute(retry_tool, retry_args),
            )
            if fixed and fixed.success and fixed.output:
                tr.error = ""
                tr.result = fixed.output


async def _blocked_by_metacognition(
    engine: Any,
    session: Any,
    tool_calls: list[dict[str, Any]],
    iteration: int,
    guidance: dict[str, Any],
) -> AsyncIterator[AgentEvent]:
    """Emit blocked tool results when metacognition halts the batch.

    Args:
        engine: The AgentEngine instance (persistence override point).
        session: The current agent session.
        tool_calls: The tool calls blocked by guidance.
        iteration: Current iteration number.
        guidance: The metacognition guidance payload.

    Yields:
        TOOL_RESULT events per blocked call plus a CHECKPOINT event.
    """
    for tc in tool_calls:
        name = (tc.get("function") or {}).get("name", "unknown")
        yield AgentEvent(
            type=AgentEventType.TOOL_RESULT,
            data={
                "id": tc.get("id", ""),
                "tool_name": name,
                "result": "blocked by metacognition resource guidance",
                "error": "resource_stop",
            },
        )
        session.messages.append(
            {
                "role": MessageRole.TOOL,
                "content": "blocked by metacognition resource guidance",
                "tool_call_id": tc.get("id", ""),
            }
        )
        await engine._persist_message(
            session.session_id,
            MessageRole.TOOL,
            content="blocked by metacognition resource guidance",
            tool_name=name,
            tool_call_id=tc.get("id", ""),
        )
    yield AgentEvent(type=AgentEventType.CHECKPOINT, data={"iteration": iteration, "tool_calls": 0, "metacognition": guidance})


async def _record_tool_result(
    engine: Any,
    session: Any,
    tr: Any,
    iteration: int,
    metacognition: Any,
    meta_guidance: dict[str, Any],
) -> AsyncIterator[AgentEvent]:
    """Record metrics and feedback for one tool result and yield its event.

    Args:
        engine: The AgentEngine instance (debug/prioritizer override points).
        session: The current agent session.
        tr: The tool execution result.
        iteration: Current iteration number.
        metacognition: Optional metacognition orchestrator for post_action.
        meta_guidance: Guidance dict accumulating feedback entries.

    Yields:
        A TOOL_RESULT event.
    """
    from app.middleware.metrics import TOOL_CALL_LATENCY, TOOL_CALL_TOTAL

    TOOL_CALL_TOTAL.labels(tool_name=tr.tool_name, status="success" if tr.success else "error").inc()
    TOOL_CALL_LATENCY.labels(tool_name=tr.tool_name).observe((tr.duration_ms or 0.0) / 1000.0)
    session.metrics.tool_call_durations.append(getattr(tr, "duration_ms", 0.0) or 0.0)
    engine.tool_prioritizer.record_outcome(tr.tool_name, tr.success, tr.duration_ms)
    try:
        if metacognition is not None:
            meta_feedback = metacognition.post_action(
                iteration,
                tr.tool_name,
                getattr(tr, "arguments", {}) or {},
                (tr.result or tr.error or "")[:500],
                tokens_used=0,
                success=bool(tr.success),
            )
            meta_guidance.setdefault("feedback", []).append(meta_feedback)
    except Exception:
        pass
    yield AgentEvent(
        type=AgentEventType.TOOL_RESULT,
        data={
            "id": tr.tool_call_id,
            "tool_name": tr.tool_name,
            "result": tr.result,
            "error": tr.error,
        },
    )
    await engine._handle_tool_debug(session, tr)
    await persist_tool_result(engine, session, tr)


async def _emit_tool_call(
    engine: Any,
    session: Any,
    tool_name: str,
    arguments: dict[str, Any],
    event_data: dict[str, Any],
    requires_approval: bool,
) -> AsyncIterator[AgentEvent]:
    """Emit a TOOL_CALL event and run the approval wait when required.

    Args:
        engine: The AgentEngine instance (timeout configuration source).
        session: The current agent session.
        tool_name: The tool being called.
        arguments: The parsed tool call arguments.
        event_data: The event data for the TOOL_CALL event.
        requires_approval: Whether the call needs interactive approval.

    Yields:
        The TOOL_CALL event.
    """
    if requires_approval:
        timeout_seconds = engine.permission_timeout_seconds
        event_data["timeout_seconds"] = timeout_seconds
        request_permission(session, event_data)
        yield AgentEvent(type=AgentEventType.TOOL_CALL, data=event_data)
        timed_out = await wait_for_permission(session, timeout_seconds)
        resolve_permission_decision(session, tool_name, arguments, timed_out)
    else:
        yield AgentEvent(type=AgentEventType.TOOL_CALL, data=event_data)


async def handle_tool_execution(
    engine: Any,
    session: Any,
    executor: Any,
    result: Any,
    iteration: int,
    ctx_tokens: int,
    metacognition: Any = None,
) -> AsyncIterator[AgentEvent]:
    """Handle tool execution from LLM response.

    Emits TOOL_CALL events (running the interactive approval flow when the
    validator requires it), executes the batch through the parallel
    executor, feeds metacognition, and emits TOOL_RESULT plus CHECKPOINT
    events.

    Args:
        engine: The AgentEngine instance (validation, persistence,
            checkpoint and debug override points).
        session: The current agent session.
        executor: The parallel tool executor.
        result: The ChatResult with tool calls.
        iteration: Current iteration number.
        ctx_tokens: Current context token count.
        metacognition: Optional metacognition orchestrator.

    Yields:
        TOOL_CALL, TOOL_RESULT, and CHECKPOINT events.
    """
    # Assign stable ids to tool calls the model left without one so the
    # assistant tool_calls entries, emitted events, executor results and tool
    # result messages all share the same id within the batch. Without this,
    # same-batch calls that lack ids would key tool results by tool name and
    # produce duplicate tool_call_id entries.
    for index, tc in enumerate(result.tool_calls):
        if not tc.get("id"):
            tc["id"] = f"tool-{iteration}-{len(session.messages)}-{index}"
    session.messages.append({"role": MessageRole.ASSISTANT, "content": "", "tool_calls": result.tool_calls})
    persisted = await engine._persist_message(session.session_id, MessageRole.ASSISTANT, content="", tool_calls=result.tool_calls)
    if getattr(session, "_continuing_input", False) and not persisted:
        raise RuntimeError("Follow-up tool calls persistence failed")

    for index, tc in enumerate(result.tool_calls):
        function = tc.get("function", {})
        arguments = parse_tool_arguments(function)
        tool_name = function.get("name", "")
        tool_call_id = tc.get("id") or f"tool-{iteration}-{len(session.messages)}-{index}"
        allowed, reason = engine._validate_tool_call(session, tool_name, arguments)
        event_data: dict[str, Any] = {"id": tool_call_id, "name": tool_name, "arguments": arguments}
        requires_approval = not allowed and isinstance(reason, dict) and reason.get("requires_approval")
        if requires_approval:
            event_data.update(reason)
            event_data["tool_call_id"] = tool_call_id
        async for event in _emit_tool_call(engine, session, tool_name, arguments, event_data, bool(requires_approval)):
            yield event

    await engine._save_checkpoint(session, {"last_tool_calls": result.tool_calls},
        pending_writes=[{"channel": "tools", "value": tc,
                         "write_id": tc.get("id") or f"{iteration}-{index}", "status": "pending"}
                        for index, tc in enumerate(result.tool_calls)])

    meta_guidance: dict[str, Any] = {}
    if metacognition is not None:
        try:
            meta_guidance = metacognition.pre_action(iteration)
            if not meta_guidance.get("proceed", True):
                async for event in _blocked_by_metacognition(engine, session, result.tool_calls, iteration, meta_guidance):
                    yield event
                return
        except Exception:
            pass

    tool_results = await executor.execute_all(result.tool_calls)
    session.metrics.total_tool_calls += len(result.tool_calls)
    for tr in tool_results:
        async for event in _record_tool_result(engine, session, tr, iteration, metacognition, meta_guidance):
            yield event

    await engine._save_checkpoint(session, {"last_tool_calls": result.tool_calls,
        "last_tool_results": [tr.result for tr in tool_results], "context_tokens": ctx_tokens})
    yield AgentEvent(type=AgentEventType.CHECKPOINT, data={"iteration": iteration, "tool_calls": len(result.tool_calls), "metacognition": meta_guidance})
