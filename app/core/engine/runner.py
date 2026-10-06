"""Core execution loop for the agent engine.

Extracted from ``app.core.agent_engine``: the run-locked orchestration, the
iteration loop, and text-result handling. Every overridable behavior
(checkpoints, persistence, validation, notifications, memory hooks,
metacognition, profile/evolution) routes through the ``AgentEngine`` facade
passed as ``engine`` so the facade override points cannot be bypassed here.
"""

from __future__ import annotations

import contextlib
import re
import time
from collections.abc import AsyncIterator
from typing import Any

from app.core import (
    AgentEvent,
    AgentEventType,
    ChatResult,
    MessageRole,
)
from app.core.compressor import ContextCompressor
from app.core.engine.iteration import compress_if_needed, prepare_iteration
from app.core.engine.llm_calls import sampling_kwargs
from app.core.engine.session_runner import merge_stream_chunk, response_usage
from app.core.task_state_machine import TaskState
from app.models.vision import build_user_content, content_text

TASK_MEMORY_MARKER = "<!-- TASK_MEMORY_CONTEXT -->"


def _meter_summarize(engine: Any, session: Any, iteration: int):
    """Build a meter callback that records a summarizer model call's usage.

    The compression step performs an extra LLM call that the main loop would
    otherwise leave out of the usage ledger. This callback forwards the
    summarize response through the engine's run store so the call is metered
    like any ordinary response.
    """
    async def meter(response: Any) -> None:
        await engine._run_store.record_response(session, response, iteration, complete=True)
        session.metrics.total_tokens_used += getattr(response, "tokens_used", 0) or 0
    return meter


async def run_locked(
    engine: Any,
    session: Any,
    message: str,
    images: list[str] | None = None,
    attachments: list[Any] | None = None,
) -> AsyncIterator[AgentEvent]:
    """Internal run method - executes under session lock.

    Args:
        engine: The AgentEngine instance providing registries and hooks.
        session: The agent session to execute.
        message: The user message to process.
        images: Optional image references for vision content.
        attachments: Optional chat attachments.

    Yields:
        AgentEvent instances during execution.
    """
    current = session.state_machine.state
    if getattr(session, "_continuing_input", False) and session._stop_requested:
        await session.state_machine.transition(TaskState.CANCELLED, trigger="user_stop")
        yield AgentEvent(type=AgentEventType.DONE, data={"status": "stopped"})
        return
    if current in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
        await session.state_machine.transition(TaskState.PENDING, trigger="user_restart")
        # A new turn begins: the interrupted-continuation marker no longer applies.
        session._resume_interrupted = False
    if session.state_machine.state != TaskState.PROCESSING:
        await session.state_machine.transition(TaskState.PROCESSING, trigger="run_start")
    resuming = session._resume_interrupted
    if not resuming:
        from app.core.prompt_optimizer import clear_reference, maybe_optimize_instruction

        clear_reference(session)
        if not getattr(session, "_continuing_input", False):
            session._stop_requested = False
        session._last_iteration = 0
        content = build_user_content(message, images, attachments)
        session.messages.append({"role": MessageRole.USER, "content": content})
        persisted = await engine._persist_message(
            session.session_id, MessageRole.USER,
            content=message, images=images,
            attachments=[{
                "kind": item.kind, "name": item.name, "mime_type": item.mime_type, "size": item.size,
            } for item in (attachments or [])],
        )
        if getattr(session, "_continuing_input", False) and not persisted:
            raise RuntimeError("Follow-up message persistence failed")
        await engine._archive_instruction(session, message)
        await maybe_optimize_instruction(engine, session, message)

    engine._set_agent_mode(session)
    engine._send_start_notification(session)
    if not resuming:
        await engine._inject_memory_context(session, message)
        await engine._inject_core_memory(session)
        await engine._inject_profile_context(session, message)

    session._last_result = None
    session._run_status_override = None
    session._last_assistant_message_id = None
    if not resuming:
        await engine._save_checkpoint(session, {})
    executor = engine._make_parallel_executor(session)
    compressor = ContextCompressor(session.context_config)
    result: ChatResult | None = None

    try:
        async with contextlib.aclosing(engine._iteration_loop(session, executor, compressor)) as events:
            async for event in events:
                yield event
    except Exception as e:
        session._last_error = str(e)
        if session._stop_requested:
            await session.state_machine.transition(TaskState.CANCELLED, trigger="user_stop")
            yield AgentEvent(type=AgentEventType.DONE, data={"status": "stopped"})
            engine._record_profile_outcome(session, message)
            engine._tick_evolution(session)
            return
        await session.state_machine.transition(TaskState.FAILED, trigger="unhandled_error")
        yield AgentEvent(type=AgentEventType.ERROR, data={"error": str(e)})
        engine._send_failure_notification(session, str(e))
        engine._record_profile_outcome(session, message)
        engine._tick_evolution(session)
        return

    if session.status.value == "failed" and session._run_status_override is None:
        engine._record_profile_outcome(session, message)
        engine._tick_evolution(session)
        return

    await engine._store_episodic_memory(session, message)
    engine._trigger_memory_reflection(session)
    engine._record_profile_outcome(session, message)
    engine._tick_evolution(session)
    result = session._last_result
    yield AgentEvent(type=AgentEventType.DONE, data={
        "status": session._run_status_override or session.status.value,
        "iterations": session._last_iteration,
        "content": result.content if result else "",
        "tokens_used": getattr(session, "_run_tokens", 0),
        "cost_status": getattr(session, "_run_cost_status", "unknown"),
        "usage_status": getattr(session, "_run_usage_status", "unknown"),
        "metrics": session.metrics.to_dict(),
        "message_id": getattr(session, "_last_assistant_message_id", None),
    })


async def iteration_loop(
    engine: Any,
    session: Any,
    executor: Any,
    compressor: Any,
) -> AsyncIterator[AgentEvent]:
    """Main iteration loop for agent execution.

    Args:
        engine: The AgentEngine instance.
        session: The agent session.
        executor: The parallel tool executor.
        compressor: The context compressor.

    Yields:
        AgentEvent instances during each iteration.
    """
    iteration = session._last_iteration if session._resume_interrupted else 0
    adapter, tools = prepare_iteration(engine, session)
    result: ChatResult | None = None
    meta_orchestrator = engine.metacognition if engine.metacognition_enabled else None
    no_progress = 0
    previous_batch = None
    if meta_orchestrator is not None:
        try:
            from app.core.metacognition import ExecutionContext

            goal_hint = content_text(session.messages[-1].get("content", "")) if session.messages else ""
            meta_orchestrator.initialize(
                ExecutionContext(
                    goal=goal_hint[:2000],
                    available_tools=[getattr(t, "name", str(t)) for t in tools],
                    token_budget=getattr(session.context_config, "max_tokens", 8000),
                )
            )
        except Exception:
            pass

    while iteration < session.max_iterations and not session._stop_requested:
        if session.status.value == "paused":
            return
        async for event in engine._consume_steering(session):
            if event.data["item"]["status"] == "applied":
                no_progress, previous_batch = 0, None
            yield event
        if session._stop_requested:
            break
        iteration += 1
        session._last_iteration = iteration
        session.metrics.total_iterations += 1
        yield AgentEvent(type=AgentEventType.THINKING, data={"iteration": iteration})

        from app.core.ui_rules import refresh_rule_context

        await refresh_rule_context(session)
        # Derived task views are rebuilt from storage, never fed into compaction.
        session.messages = [msg for msg in session.messages if not (
            msg.get("role") == MessageRole.SYSTEM
            and isinstance(msg.get("content"), str)
            and msg["content"].startswith(TASK_MEMORY_MARKER)
        )]
        compressed, ctx_tokens = await compress_if_needed(
            session, adapter, compressor, meter=_meter_summarize(engine, session, iteration),
        )
        if compressed is not None:
            yield AgentEvent(type=AgentEventType.CONTEXT_COMPRESSION,
                             data={"iteration": iteration, "tokens": ctx_tokens,
                                   "limit": getattr(adapter.capabilities, "max_tokens", None)
                                    or session.context_config.max_tokens})

        context_limit = min(session.context_config.max_tokens,
                            getattr(adapter.capabilities, "max_tokens", None)
                            or session.context_config.max_tokens)
        await engine._inject_task_memory_context(  # noqa: SLF001
            session, token_budget=min(2048, max(0, context_limit // 4)),
        )

        if adapter.capabilities.streaming:
            result = ChatResult()
            started = time.monotonic()
            try:
                async for chunk in adapter.stream_chat(messages=session.messages, tools=tools or None, **sampling_kwargs(session)):
                    delta = merge_stream_chunk(result, chunk)
                    if session._stop_requested:
                        await engine._run_store.record_response(session, result, iteration, complete=False)
                        session.metrics.total_tokens_used += result.tokens_used
                        result = None
                        break
                    if delta:
                        yield AgentEvent(type=AgentEventType.TEXT, data={"content": delta})
                    engine._accumulate_stream_tool_calls(result.tool_calls, chunk.tool_calls)
            except BaseException:
                if result is not None:
                    await engine._run_store.record_response(session, result, iteration, complete=False)
                    session.metrics.total_tokens_used += result.tokens_used
                raise
            finally:
                session.metrics.llm_call_durations.append(time.monotonic() - started)
            if result is not None:
                result.finish_reason = result.finish_reason or ("tool_calls" if result.tool_calls else "stop")
        else:
            result = await engine._call_llm_with_resilience(session, adapter, session.messages, iteration)
        if result is None:
            if session._stop_requested:
                await session.state_machine.transition(TaskState.CANCELLED, trigger="user_stop")
                yield AgentEvent(type=AgentEventType.DONE, data={"status": "stopped"})
            else:
                session._last_error = "LLM call failed or stopped"
                await session.state_machine.transition(TaskState.FAILED, trigger="llm_stopped")
                yield AgentEvent(type=AgentEventType.ERROR, data={"error": "LLM call failed or stopped"})
            break
        session._last_result = result
        result.tokens_used = response_usage(result)["total_tokens"] or 0
        await engine._run_store.record_response(session, result, iteration, complete=result.finish_reason != "error")
        session.metrics.total_tokens_used += getattr(result, "tokens_used", 0) or 0
        if session.status.value == "paused":
            await engine._save_checkpoint(session, {"paused": True})
            return
        if result.finish_reason == "error":
            raise RuntimeError("Model reported an error response")

        if result.content:
            async for event in engine._handle_text_result(session, result, adapter):
                yield event

        if not result.tool_calls and not (result.content or "").strip():
            if previous_batch is not None:
                no_progress = 0
            previous_batch = None
            no_progress += 1
            if no_progress >= 2:
                session._last_error = "Two consecutive empty model responses"
                session._run_status_override = "no_progress"
                await session.state_machine.transition(TaskState.PAUSED, trigger="no_progress")
                await engine._save_checkpoint(session, {"no_progress": session._last_error})
                yield AgentEvent(type=AgentEventType.PROGRESS, data={"status": "paused", "reason": session._last_error})
                return
            session.messages.append({
                "role": MessageRole.SYSTEM,
                "content": "Your previous response was empty. Please provide a helpful response or use an appropriate tool.",
            })
            continue

        if result.tool_calls:
            batch = []
            async for _event in engine._handle_tool_execution(session, executor, result, iteration, ctx_tokens, metacognition=meta_orchestrator):
                if _event.type == AgentEventType.TOOL_RESULT:
                    batch.append(_event.data)
                yield _event
            from app.core.engine.input_queue import stalled_batch

            evidence = stalled_batch(result.tool_calls, batch) if not (result.content or "").strip() else None
            no_progress = no_progress + 1 if evidence is not None and evidence == previous_batch else 0
            previous_batch = evidence
            if no_progress >= 2 and not session._stop_requested:
                session._last_error = "Two repeated tool batches with unchanged read-only results"
                session._run_status_override = "no_progress"
                await session.state_machine.transition(TaskState.PAUSED, trigger="no_progress")
                await engine._save_checkpoint(session, {"no_progress": session._last_error})
                yield AgentEvent(type=AgentEventType.PROGRESS, data={"status": "paused", "reason": session._last_error})
                return
            continue

        steered = False
        async for event in engine._consume_steering(session):
            steered = steered or event.data["item"]["status"] == "applied"
            yield event
        no_progress, previous_batch = 0, None
        if steered:
            continue
        if not session._stop_requested:
            # Pi dual-loop G1: outer-loop continue decision at the natural turn end.
            # Opt-in only; may enqueue a follow_up so the outer loop auto-continues.
            await engine.maybe_generate_followup(session, result)
        break

    if session.status.value == "failed":
        return
    if not session._stop_requested and iteration >= session.max_iterations and (result is None or result.tool_calls or not result.content):
        await session.state_machine.transition(TaskState.FAILED, trigger="max_iterations")
        session._run_status_override = "max_iterations_reached"
        session._last_error = "Maximum iterations reached"
        engine._send_failure_notification(session, session._last_error)
        await engine._save_checkpoint(session, {"final_result": result.content if result else ""})
        return

    if session._stop_requested:
        await session.state_machine.transition(TaskState.CANCELLED, trigger="user_stop")
    else:
        await session.state_machine.transition(TaskState.COMPLETED, trigger="run_complete")
        engine._send_completion_notification(session, result)
    await engine._save_checkpoint(session, {"final_result": result.content if result else ""})
    yield AgentEvent(type=AgentEventType.CHECKPOINT, data={"iteration": iteration, "final": True})


async def handle_text_result(
    engine: Any,
    session: Any,
    result: Any,
    adapter: Any,
) -> AsyncIterator[AgentEvent]:
    """Handle text content from LLM response.

    Args:
        engine: The AgentEngine instance (persistence override point).
        session: The current session.
        result: The ChatResult.
        adapter: The LLM adapter.

    Yields:
        TEXT events for non-streaming path.
    """
    from app.models.openai_adapter import OpenAIAdapter

    if not result.tool_calls and result.content:
        xml_tool_calls = OpenAIAdapter._parse_xml_tool_calls(result.content)
        if xml_tool_calls:
            result.tool_calls = xml_tool_calls
            cleaned = re.sub(r"<function([^>]+)>.*?</\1>", "", result.content, flags=re.DOTALL | re.IGNORECASE).strip()
            if not cleaned:
                result.content = ""

    session.messages.append({"role": MessageRole.ASSISTANT, "content": result.content})
    persisted_id = await engine._persist_message(session.session_id, MessageRole.ASSISTANT, content=result.content, tokens=getattr(result, "tokens_used", 0))
    if getattr(session, "_continuing_input", False) and not persisted_id:
        raise RuntimeError("Follow-up response persistence failed")
    if persisted_id:
        session._last_assistant_message_id = persisted_id
    if not (adapter.capabilities and adapter.capabilities.streaming):
        yield AgentEvent(type=AgentEventType.TEXT, data={"content": result.content})
