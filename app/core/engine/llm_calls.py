"""LLM call helpers for the agent engine.

Extracted from ``app.core.agent_engine``: resilient calls, stream
accumulation, and streamed tool-call delta merging. Tool building goes
through the engine override point so the facade remains the patch seam.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from app.core import ChatResult
from app.core.engine.session_runner import merge_stream_chunk
from app.core.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    RetryExhaustedError,
    TimeoutConfig,
)


def accumulate_stream_tool_calls(
    accumulated: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
) -> None:
    """Merge streamed tool call deltas into complete tool calls.

    Args:
        accumulated: The list of accumulated tool calls (mutated in place).
        chunks: The streamed tool call deltas to merge.
    """
    for position, tool_call in enumerate(chunks):
        call_id = tool_call.get("id")
        existing = next(
            (i for i, call in enumerate(accumulated) if call_id and call.get("id") == call_id), None
        )
        if "index" in tool_call:
            index = tool_call["index"]
        elif existing is not None:
            index = existing
        elif call_id and position < len(accumulated) and accumulated[position].get("id"):
            index = len(accumulated)
        else:
            index = position
        while len(accumulated) <= index:
            accumulated.append(
                {
                    "id": "",
                    "type": "function",
                    "function": {"name": "", "arguments": ""},
                }
            )
        target = accumulated[index]
        if tool_call.get("id"):
            target["id"] = tool_call["id"]
        function = tool_call.get("function", {})
        if function.get("name"):
            target["function"]["name"] = function["name"]
        if function.get("arguments") is not None:
            arguments = function["arguments"]
            if isinstance(arguments, dict):
                arguments = json.dumps(arguments, ensure_ascii=False)
            elif not isinstance(arguments, str):
                arguments = str(arguments)
            if isinstance(function["arguments"], dict):
                target["function"]["arguments"] = arguments
            else:
                target["function"]["arguments"] += arguments


async def stream_accumulate(
    adapter: Any,
    messages: list[dict[str, Any]],
    tools: list,
    sampling: dict[str, Any] | None = None,
) -> ChatResult:
    """Accumulate a streaming response into a single ChatResult.

    When the adapter reports authoritative cumulative content
    (accumulated_content), it is trusted as-is; otherwise per-chunk
    deltas are appended. No prefix-based dedup heuristic is needed.

    Args:
        adapter: The LLM adapter with a ``stream_chat`` method.
        messages: The messages to send.
        tools: Available tool definitions.
        sampling: Optional per-call sampling overrides (temperature /
            max_tokens) forwarded to the adapter as request parameters.

    Returns:
        A ChatResult with accumulated content and tool calls.
    """
    result = ChatResult()
    async for chunk in adapter.stream_chat(
        messages=messages, tools=tools or None, **(sampling or {})
    ):
        merge_stream_chunk(result, chunk)
        if getattr(chunk, "tool_calls", None):
            accumulate_stream_tool_calls(result.tool_calls, chunk.tool_calls)
    if result.finish_reason is None:
        result.finish_reason = "tool_calls" if result.tool_calls else "stop"
    return result


def sampling_kwargs(session: Any) -> dict[str, Any]:
    """Per-session LLM sampling overrides to forward to the model adapter.

    Returns ``{}`` unless the session explicitly sets ``temperature`` /
    ``max_tokens`` (e.g. workflow LLM nodes), so provider defaults apply
    everywhere else.
    """
    kwargs: dict[str, Any] = {}
    temperature = getattr(session, "temperature", None)
    if temperature is not None:
        kwargs["temperature"] = temperature
    max_tokens = getattr(session, "max_tokens", None)
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    return kwargs


async def stream_chat(adapter: Any, session: Any, tools: list) -> ChatResult | None:
    """Handle streaming chat response for a session.

    Args:
        adapter: The LLM adapter.
        session: The current session.
        tools: Available tool definitions.

    Returns:
        ChatResult with accumulated content, or None if stopped.
    """
    result = ChatResult()
    async for chunk in adapter.stream_chat(
        messages=session.messages, tools=tools or None, **sampling_kwargs(session)
    ):
        if session._stop_requested:
            return None
        merge_stream_chunk(result, chunk)
        accumulate_stream_tool_calls(result.tool_calls, chunk.tool_calls)
    result.finish_reason = result.finish_reason or ("tool_calls" if result.tool_calls else "stop")
    return result


async def call_llm(adapter: Any, session: Any, tools: list) -> ChatResult | None:
    """Call the LLM adapter and return the result.

    Args:
        adapter: The LLM adapter.
        session: The current session.
        tools: Available tool definitions.

    Returns:
        ChatResult or None if stopped.
    """
    from app.core.task_state_machine import TaskState

    if session._stop_requested:
        await session.state_machine.transition(TaskState.CANCELLED, trigger="user_stop")
        return None
    return await adapter.chat(
        messages=session.messages, tools=tools or None, **sampling_kwargs(session)
    )


async def call_llm_with_resilience(
    engine: Any,
    session: Any,
    model_adapter: Any,
    messages: list[dict[str, Any]],
    iteration: int,
) -> ChatResult:
    """Call the LLM through the retry handler and circuit breaker.

    Args:
        engine: The AgentEngine instance (tool building override point).
        session: The current session.
        model_adapter: The LLM adapter.
        messages: The messages to send.
        iteration: The current iteration number.

    Returns:
        The ChatResult from the model.

    Raises:
        RetryExhaustedError: If the call fails after retries are exhausted.
        CircuitBreakerOpenError: If the circuit breaker is open.
    """
    config = session.session_config
    timeout_config = config.timeouts or TimeoutConfig()
    circuit_config = config.circuit_breaker or CircuitBreakerConfig()
    breaker = session._circuit_breaker or CircuitBreaker(
        name=f"session-{session.session_id or 'default'}",
        config=circuit_config,
    )
    session._circuit_breaker = breaker

    task_description = session.messages[-1].get("content", "") if session.messages else ""
    tools = engine._build_tools_for_session(session, task_description=task_description)
    sampling = sampling_kwargs(session)

    start = time.monotonic()
    try:

        async def _single() -> ChatResult:
            if model_adapter.capabilities and getattr(
                model_adapter.capabilities, "streaming", False
            ):
                return await stream_accumulate(
                    model_adapter, messages or session.messages, tools, sampling
                )
            return await model_adapter.chat(
                messages=messages or session.messages, tools=tools or None, **sampling
            )

        async def _attempt() -> ChatResult:
            return await asyncio.wait_for(_single(), timeout=timeout_config.per_call_seconds)

        try:
            return await breaker.call(_attempt)
        except CircuitBreakerOpenError:
            raise
        except RetryExhaustedError:
            raise
        except TimeoutError:
            session.metrics.retry_count += 1
            raise RetryExhaustedError("LLM call timed out") from None
        except Exception as e:
            raise e
    finally:
        session.metrics.llm_call_durations.append(time.monotonic() - start)
