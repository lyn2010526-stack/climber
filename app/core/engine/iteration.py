"""Iteration sub-steps for the agent engine.

Extracted from ``app.core.agent_engine``: adapter/tool preparation, context
compression, and checkpoint persistence.
"""

from __future__ import annotations

from typing import Any

from app.core.compressor import estimate_tokens


def prepare_iteration(engine: Any, session: Any) -> tuple[Any, list[dict[str, Any]]]:
    """Prepare the LLM adapter and tool definitions for an iteration loop.

    Tool definitions are built through the engine's override point so the
    facade stays the single composition root for tool building.

    Args:
        engine: The AgentEngine instance providing registries.
        session: The agent session providing provider/model credentials and
            the enabled tool names.

    Returns:
        A tuple of (adapter, tools).
    """
    from app.models.vision import content_text

    adapter = engine.model_registry.get_or_create(
        provider=session.provider,
        model_id=session.model_id,
        api_key=session.api_key,
        base_url=session.base_url,
    )
    task_description = content_text(session.messages[-1].get("content", "")) if session.messages else ""
    tools = engine._build_tools_for_session(session, task_description=task_description)
    return adapter, tools


async def compress_if_needed(
    session: Any,
    adapter: Any,
    compressor: Any,
    *,
    meter=None,
) -> tuple[list[dict[str, Any]] | None, int]:
    """Compress session messages when the context grows too large.

    Checks the compressor's own trigger condition and the token usage against
    the adapter/session context limit (80% threshold). When compression is
    triggered, ``session.messages`` is replaced with the compressed messages.

    Args:
        session: The agent session whose messages may be compressed.
        adapter: The LLM adapter, used for capabilities and compression.
        compressor: The context compressor deciding and performing compression.
        meter: Optional callback receiving the summarize response so the
            caller can meter the extra model call's token usage.

    Returns:
        A tuple of (messages, ctx_tokens). ``messages`` is the compressed list
        when compression happened, else None. ``ctx_tokens`` is the estimate
        taken before compression.
    """
    ctx_tokens = estimate_tokens(session.messages)
    ctx_limit = getattr(adapter.capabilities, "max_tokens", None) or session.context_config.max_tokens
    if compressor.needs_compression(session.messages) or (ctx_limit and ctx_tokens > ctx_limit * 0.8):
        compressed = await compressor.compress(session.messages, adapter, meter=meter)
        session.messages = compressed
        return compressed, ctx_tokens
    return None, ctx_tokens


async def save_checkpoint(
    checkpoint_store: Any,
    session: Any,
    channels: dict[str, Any],
    pending_writes: list[dict[str, Any]] | None = None,
) -> str:
    """Persist a sanitized checkpoint snapshot of the session.

    Builds a CheckpointData from the session's current messages, iteration and
    state machine status, sanitizes it (removing secrets), saves it through the
    checkpoint store and records the new checkpoint id on the session.

    Args:
        checkpoint_store: Store used to persist the checkpoint data.
        session: The agent session to snapshot.
        channels: Channel values to store alongside the checkpoint.
        pending_writes: Optional pending writes to attach to the checkpoint.

    Returns:
        The checkpoint id assigned by the checkpoint store.
    """
    from uuid import uuid4

    from app.core.checkpoint import CheckpointData, sanitize_checkpoint

    cp = CheckpointData(
        session_id=session.session_id, messages=session.messages,
        iteration=session._last_iteration, status=session.state_machine.state.value,
        metadata={"thread_id": session.current_turn_id or "", "error": session._last_error},
        channel_values=channels, channel_versions={"messages": session._last_iteration},
        versions_seen={"node": {"messages": session._last_iteration}},
        pending_writes=pending_writes or [],
    )
    cp = sanitize_checkpoint(cp, secrets=(session.api_key,))
    cid = await checkpoint_store.save(None, cp,
        thread_id=session.current_turn_id or "", checkpoint_id=str(uuid4()),
        parent_id=getattr(session, "_last_checkpoint_id", None))
    session._last_checkpoint_id = cid
    return cid
