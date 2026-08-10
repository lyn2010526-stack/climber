"""Worker executor—produces deliverables using tools with context compression.

Integrates ContextCompressor to automatically handle long conversations that
exceed model token limits. Old messages are compressed via LLM summarization
while recent messages are preserved intact.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.core import ContextConfig
from app.core.collab_prompts import get_worker_prompt
from app.core.compressor import ContextCompressor, estimate_tokens
from app.core.di import resolve as di_resolve
from app.core.stream_events import (
    CollabEvent,
    CollabEventType,
    make_context_compression,
    make_text_delta,
    make_worker_tool_call,
    make_worker_tool_result,
)
from app.core.tool_bridge import ToolBridge

logger = structlog.get_logger()


@dataclass
class WorkerOutput:
    """Output from a Worker execution."""

    content: str
    tool_calls: list[dict[str, Any]]
    tokens_used: int
    success: bool
    error: str | None = None


@dataclass
class _MemberInfo:
    """Lightweight member info for execution."""

    id: str
    name: str
    provider: str
    model_id: str
    api_key: str
    avatar_url: str | None = None
    tools: list[str] = field(default_factory=list)


class WorkerExecutor:
    """Executes Worker role: produces deliverables using tools with context management."""

    def __init__(
        self,
        session_id: str,
        tool_bridge: ToolBridge | None = None,
        context_config: ContextConfig | None = None,
    ):
        self._session_id = session_id
        self._tool_bridge = tool_bridge or ToolBridge()
        self._compressor = ContextCompressor(context_config or ContextConfig())

    async def execute(
        self,
        member: _MemberInfo,
        task: str,
        feedback: str,
        history: list[dict[str, str]],
    ) -> AsyncIterator[CollabEvent]:
        """Execute Worker task with automatic context compression.

        If history + task exceeds the token budget, old messages are
        automatically compressed via LLM summarization.
        """
        yield CollabEvent(
            type=CollabEventType.WORKER_START,
            session_id=self._session_id,
            member_id=member.id,
            member_name=member.name,
            member_avatar=member.avatar_url,
            data={"model": f"{member.provider}/{member.model_id}"},
        )

        # Build prompt with history
        history_text = self._format_history(history)
        system_prompt = get_worker_prompt(
            name=member.name,
            task=task,
            feedback=feedback,
            history=history_text,
        )

        try:
            model_registry = di_resolve("ModelRegistry")
            adapter = model_registry.get_or_create(
                provider=member.provider,
                model_id=member.model_id,
                api_key=member.api_key,
            )
        except Exception as e:
            yield CollabEvent(
                type=CollabEventType.ERROR,
                session_id=self._session_id,
                member_id=member.id,
                data={"error": f"Model init failed: {e!s}"},
            )
            return

        # Build messages array for compression check
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task},
        ]
        if feedback:
            messages.append({"role": "user", "content": f"Reviewer feedback:\n{feedback}\n\nPlease fix the issues and regenerate."})

        # Check and apply context compression if needed
        if self._compressor.needs_compression(messages):
            original_tokens = estimate_tokens(messages)
            messages = await self._compressor.compress(messages, adapter)
            compressed_tokens = estimate_tokens(messages)
            logger.info(
                "Context compressed for worker",
                session_id=self._session_id,
                original_tokens=original_tokens,
                compressed_tokens=compressed_tokens,
            )
            yield make_context_compression(session_id=self._session_id, original_tokens=original_tokens, compressed_tokens=compressed_tokens)

        # Get available tools
        tools = self._tool_bridge.list_tools(member.tools or None, is_worker=True)

        # Stream chat with tool support
        full_content = ""
        all_tool_calls: list[dict[str, Any]] = []
        total_tokens = 0

        try:
            async for chunk in adapter.stream_chat(messages=messages, tools=tools or None):
                if chunk.content:
                    full_content += chunk.content
                    yield make_text_delta(
                        session_id=self._session_id,
                        member_id=member.id,
                        member_name=member.name,
                        delta=chunk.content,
                        avatar=member.avatar_url,
                    )

                if chunk.tool_calls:
                    for tc in chunk.tool_calls:
                        tool_name = tc.get("function", {}).get("name", "")
                        tool_args_str = tc.get("function", {}).get("arguments", "{}")
                        try:
                            tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                        except json.JSONDecodeError:
                            tool_args = {}

                        all_tool_calls.append({"name": tool_name, "arguments": tool_args})

                        yield make_worker_tool_call(
                            session_id=self._session_id,
                            member_id=member.id,
                            member_name=member.name,
                            tool_name=tool_name,
                            arguments=tool_args,
                            avatar=member.avatar_url,
                        )

                        result = await self._tool_bridge.execute(tool_name, tool_args)

                        yield make_worker_tool_result(
                            session_id=self._session_id,
                            member_id=member.id,
                            member_name=member.name,
                            tool_name=tool_name,
                            result=result.output[:2000],
                            avatar=member.avatar_url,
                        )

                        # Feed tool result back to model
                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [tc],
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.get("id", ""),
                            "content": result.output,
                        })

                if chunk.tokens_used:
                    total_tokens = chunk.tokens_used

        except Exception as e:
            logger.error("Worker execution failed", error=str(e), member=member.name)
            yield CollabEvent(
                type=CollabEventType.ERROR,
                session_id=self._session_id,
                member_id=member.id,
                data={"error": str(e)},
            )
            return

        # Emit done event
        yield CollabEvent(
            type=CollabEventType.WORKER_DONE,
            session_id=self._session_id,
            member_id=member.id,
            member_name=member.name,
            member_avatar=member.avatar_url,
            data={
                "content": full_content,
                "tool_calls": all_tool_calls,
                "tokens_used": total_tokens,
            },
        )

    def _format_history(self, history: list[dict[str, str]]) -> str:
        """Format discussion history for prompt injection."""
        if not history:
            return "No previous discussion."
        lines = []
        for msg in history[-10:]:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:500]
            lines.append(f"[{role}] {content}")
        return "\n".join(lines)
