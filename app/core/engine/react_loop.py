from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING, Any

import structlog

from app.core import AgentEvent, AgentEventType, ChatResult, CheckpointData
from app.core.compressor import ContextCompressor, estimate_tokens
from app.core.engine.session import AgentSession
from app.core.parallel import ParallelToolExecutor
from app.core.task_state_machine import TaskState
from app.models.openai_adapter import OpenAIAdapter

if TYPE_CHECKING:
    from app.core.checkpoint import InMemoryCheckpointStore
    from app.core.tool_prioritizer import ToolPrioritizer
    from app.models.registry import ModelRegistry
    from app.tools import ToolRegistry

logger = structlog.get_logger()


class ReActLoopExecutor:
    def __init__(
        self,
        model_registry: ModelRegistry,
        tool_registry: ToolRegistry,
        checkpoint_store: InMemoryCheckpointStore,
        tool_prioritizer: ToolPrioritizer,
        build_tools_fn: Callable[[list[str], str], list[dict[str, Any]]],
        validate_tool_call_fn: Callable[[str, dict[str, Any]], tuple[bool, str]] | None = None,
    ):
        self.model_registry = model_registry
        self.tool_registry = tool_registry
        self._checkpoints = checkpoint_store
        self.tool_prioritizer = tool_prioritizer
        self._build_tools_fn = build_tools_fn
        self._validate_tool_call_fn = validate_tool_call_fn

    async def execute(
        self,
        session: AgentSession,
        message: str,
        on_error: Callable[[str], None] | None = None,
    ) -> AsyncIterator[AgentEvent]:
        iteration = 0
        executor = ParallelToolExecutor(
            self.tool_registry,
            validator=self._validate_tool_call_fn,
            session=session,
        )
        compressor = ContextCompressor(session.context_config)
        result: ChatResult | None = None

        try:
            adapter = self.model_registry.get_or_create(
                provider=session.provider,
                model_id=session.model_id,
                api_key=session.api_key,
                base_url=session.base_url,
            )

            tools = self._build_tools_fn(session.tools, task_description=message)

            while iteration < session.max_iterations and not session._stop_requested:
                iteration += 1

                ctx_tokens = estimate_tokens(session.messages)
                ctx_limit = getattr(adapter.capabilities, "max_tokens", None) or session.context_config.max_tokens
                if compressor.needs_compression(session.messages) or (ctx_limit and ctx_tokens > ctx_limit * 0.8):
                    session.messages = await compressor.compress(session.messages, adapter)
                    yield AgentEvent(type=AgentEventType.CONTEXT_COMPRESSION, data={"iteration": iteration, "tokens": ctx_tokens, "limit": ctx_limit})

                yield AgentEvent(type=AgentEventType.THINKING, data={"iteration": iteration})

                try:
                    if adapter.capabilities.streaming:
                        full_content = ""
                        accumulated_tool_calls = []
                        async for chunk in adapter.stream_chat(messages=session.messages, tools=tools or None):
                            if chunk.content:
                                full_content += chunk.content
                                yield AgentEvent(type=AgentEventType.TEXT, data={"content": chunk.content})
                            for tc in chunk.tool_calls:
                                idx = tc.get("index", 0) if "index" in tc else 0
                                while len(accumulated_tool_calls) <= idx:
                                    accumulated_tool_calls.append({
                                        "id": "",
                                        "type": "function",
                                        "function": {"name": "", "arguments": ""},
                                    })
                                if tc.get("id"):
                                    accumulated_tool_calls[idx]["id"] = tc["id"]
                                if tc.get("function", {}).get("name"):
                                    accumulated_tool_calls[idx]["function"]["name"] = tc["function"]["name"]
                                if tc.get("function", {}).get("arguments"):
                                    new_args = tc["function"]["arguments"]
                                    if isinstance(new_args, dict):
                                        new_args = json.dumps(new_args, ensure_ascii=False)
                                    elif not isinstance(new_args, str):
                                        new_args = str(new_args)
                                    accumulated_tool_calls[idx]["function"]["arguments"] += new_args
                        result = ChatResult(content=full_content, tool_calls=accumulated_tool_calls, finish_reason="stop", tokens_used=0)
                    else:
                        result = await adapter.chat(messages=session.messages, tools=tools or None)
                except Exception as e:
                    if session._stop_requested:
                        yield AgentEvent(type=AgentEventType.ERROR, data={"error": str(e)})
                        await session.state_machine.transition(TaskState.CANCELLED, trigger="user_stop")
                        return
                    yield AgentEvent(type=AgentEventType.ERROR, data={"error": str(e)})
                    await session.state_machine.transition(TaskState.FAILED, trigger="llm_error")
                    if on_error:
                        on_error(str(e))
                    return

                if not result.tool_calls and result.content:
                    xml_tool_calls = OpenAIAdapter._parse_xml_tool_calls(result.content)
                    if xml_tool_calls:
                        result.tool_calls = xml_tool_calls
                        cleaned = re.sub(r'<function([^>]+)>.*?</\1>', '', result.content, flags=re.DOTALL | re.IGNORECASE).strip()
                        if not cleaned:
                            result.content = ""

                if result.content:
                    session.messages.append({"role": "assistant", "content": result.content})
                    yield AgentEvent(type=AgentEventType.TEXT, data={"content": result.content})

                if result.tool_calls:
                    session.messages.append({"role": "assistant", "content": "", "tool_calls": result.tool_calls})
                    for tc in result.tool_calls:
                        yield AgentEvent(type=AgentEventType.TOOL_CALL, data={"id": tc.get("id"), "name": tc.get("function", {}).get("name"), "arguments": tc.get("function", {}).get("arguments", {})})
                    tool_results = await executor.execute_all(result.tool_calls)
                    for tr in tool_results:
                        self.tool_prioritizer.record_outcome(
                            tr.tool_name,
                            tr.success,
                            tr.duration_ms,
                        )
                        yield AgentEvent(type=AgentEventType.TOOL_RESULT, data={"tool_name": tr.tool_name, "result": tr.result, "error": tr.error})
                        session.messages.append({"role": "tool", "content": tr.error or tr.result, "tool_name": tr.tool_name})

                    cp = CheckpointData(
                        session_id=session.session_id,
                        messages=session.messages,
                        iteration=iteration,
                        status=session.state_machine.state.value,
                        channel_values={
                            "last_tool_calls": result.tool_calls,
                            "last_tool_results": [tr.error or tr.result for tr in tool_results],
                            "context_tokens": ctx_tokens,
                        },
                        channel_versions={"messages": iteration, "tools": len(result.tool_calls)},
                        versions_seen={"node": {"messages": iteration, "tools": len(result.tool_calls)}},
                    )
                    await self._checkpoints.save(None, cp, checkpoint_id=f"{session.session_id}-{iteration}")
                    yield AgentEvent(type=AgentEventType.CHECKPOINT, data={"iteration": iteration, "tool_calls": len(result.tool_calls)})
                    continue

                cp = CheckpointData(
                    session_id=session.session_id,
                    messages=session.messages,
                    iteration=iteration,
                    status=session.state_machine.state.value,
                    channel_values={
                        "final_content": result.content,
                        "total_iterations": iteration,
                        "context_tokens": ctx_tokens,
                    },
                    channel_versions={"messages": iteration},
                    versions_seen={"node": {"messages": iteration}},
                )
                await self._checkpoints.save(None, cp, checkpoint_id=f"{session.session_id}-{iteration}")
                yield AgentEvent(type=AgentEventType.CHECKPOINT, data={"iteration": iteration})
                break

            if iteration >= session.max_iterations and result and result.tool_calls:
                await session.state_machine.transition(TaskState.FAILED, trigger="max_iterations")
                yield AgentEvent(type=AgentEventType.DONE, data={"status": "max_iterations_reached", "iterations": iteration})
                return

            if session._stop_requested:
                await session.state_machine.transition(TaskState.CANCELLED, trigger="user_stop")
            else:
                await session.state_machine.transition(TaskState.COMPLETED, trigger="run_complete")

        except Exception as e:
            if session._stop_requested:
                await session.state_machine.transition(TaskState.CANCELLED, trigger="user_stop")
            else:
                await session.state_machine.transition(TaskState.FAILED, trigger="unhandled_error")
            yield AgentEvent(type=AgentEventType.ERROR, data={"error": str(e)})
            if on_error:
                on_error(str(e))
            return

        yield AgentEvent(
            type=AgentEventType.DONE,
            data={
                "status": session.status.value,
                "iterations": iteration,
                "content": result.content if result else "",
                "tokens_used": getattr(result, "tokens_used", 0) if result else 0,
            },
        )
