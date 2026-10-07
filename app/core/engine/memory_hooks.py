"""Memory injection and episodic storage hooks for the agent engine.

Extracted from ``app.core.agent_engine``. These functions are invoked
through the ``AgentEngine`` facade methods so tests and subclasses can
override the entry points.
"""

from __future__ import annotations

from contextlib import suppress
from typing import Any

import structlog

from app.core.compressor import ContextBlock

logger = structlog.get_logger()


def _diagnose(session: Any, hook: str, exc: Exception) -> None:
    """Keep hook failures observable while preserving best-effort behavior."""
    diagnostics = getattr(session, "memory_hook_diagnostics", None)
    if not isinstance(diagnostics, list):
        diagnostics = []
        with suppress(Exception):
            session.memory_hook_diagnostics = diagnostics
    diagnostics.append({"hook": hook, "error": str(exc), "type": type(exc).__name__})
    logger.warning("memory_hook_failed", hook=hook, error=str(exc), error_type=type(exc).__name__)


def set_agent_mode(session: Any) -> None:
    """Set the current agent mode for tool execution context.

    Args:
        session: The agent session.
    """
    try:
        from app.core.file_patch import set_current_agent_mode

        set_current_agent_mode(session.mode)
    except Exception as exc:
        _diagnose(session, "set_agent_mode", exc)


async def inject_memory_context(engine: Any, session: Any, message: str) -> None:
    """Inject relevant memories into session context.

    Args:
        engine: The AgentEngine instance providing the memory service.
        session: The agent session.
        message: The user query for memory retrieval.
    """
    try:
        memory_context = await engine.memory_service.format_memories_for_prompt(
            user_id=session.user_id,
            query=message,
            max_memories=5,
        )
        memory_marker = "<!-- MEMORY_CONTEXT -->"
        if memory_context:
            for i, msg in enumerate(session.messages):
                if msg.get("content", "").startswith(memory_marker):
                    session.messages[i] = ContextBlock(
                        memory_marker + "\n" + memory_context, "memory", "untrusted", True
                    ).as_message()
                    break
            else:
                session.messages.insert(
                    -1,
                    ContextBlock(
                        memory_marker + "\n" + memory_context, "memory", "untrusted", True
                    ).as_message(),
                )
        else:
            session.messages[:] = [
                msg
                for msg in session.messages
                if not msg.get("content", "").startswith(memory_marker)
            ]
    except Exception as exc:
        _diagnose(session, "inject_memory_context", exc)


async def inject_core_memory(session: Any) -> None:
    """Inject core memory blocks into session context.

    Args:
        session: The agent session.
    """
    try:
        from app.core.core_memory import core_memory

        blocks = await core_memory.get_blocks(user_id=session.user_id, agent_id=session.agent_id)
        core_marker = "<!-- CORE_MEMORY -->"
        if blocks:
            core_memory_xml = core_memory.format_for_prompt(blocks)
            for i, msg in enumerate(session.messages):
                if msg.get("content", "").startswith(core_marker):
                    session.messages[i] = ContextBlock(
                        core_marker + "\n" + core_memory_xml, "core_memory", "untrusted", True
                    ).as_message()
                    break
            else:
                session.messages.insert(
                    -1,
                    ContextBlock(
                        core_marker + "\n" + core_memory_xml, "core_memory", "untrusted", True
                    ).as_message(),
                )
        else:
            session.messages[:] = [
                msg
                for msg in session.messages
                if not msg.get("content", "").startswith(core_marker)
            ]
    except Exception as exc:
        _diagnose(session, "inject_core_memory", exc)


async def store_episodic_memory(engine: Any, session: Any, message: str) -> None:
    """Store important interaction in episodic memory.

    Args:
        engine: The AgentEngine instance providing the memory service.
        session: The agent session.
        message: The user message.
    """
    try:
        result = getattr(session, "_last_result", None)
        if result and result.content and len(result.content) > 10:
            await engine.memory_service.create_episodic_memory(
                user_id=session.user_id,
                content=f"User: {message}\nAssistant: {result.content[:500]}",
                agent_id=session.agent_id,
                source_session_id=session.session_id,
                importance=0.7,
            )
    except Exception as exc:
        _diagnose(session, "store_episodic_memory", exc)


def trigger_memory_reflection(engine: Any, session: Any) -> None:
    """Trigger memory reflection (fire-and-forget).

    Args:
        engine: The AgentEngine instance providing the spawn hook.
        session: The agent session.
    """
    try:
        from app.core.memory_reflection import memory_reflection

        engine._spawn(memory_reflection.maybe_reflect(session.user_id))
    except Exception as exc:
        _diagnose(session, "trigger_memory_reflection", exc)


async def archive_instruction(session: Any, message: str) -> None:
    """Persist the verbatim instruction and its safe local parse.

    Args:
        session: The agent session.
        message: The user instruction of this run.
    """
    try:
        from app.core.instruction import understand_instruction
        from app.storage import async_session
        from app.storage.repository_instruction_traces import create_trace

        understanding = understand_instruction(message, context=session.session_id)
        async with async_session() as db:
            trace, _ = await create_trace(
                db,
                {
                    **understanding.to_trace_payload(
                        session_id=getattr(session, "session_id", None),
                        user_id=session.user_id,
                    ),
                    "turn_id": getattr(session, "current_turn_id", None),
                    "status": "running",
                },
            )
            await db.commit()
        session._instruction_trace_id = trace.id
    except Exception as exc:
        import structlog

        structlog.get_logger().warning("instruction_trace_archive_failed", error=str(exc))
