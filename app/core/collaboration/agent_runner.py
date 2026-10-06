"""Agent execution with retry and fallback for group collaboration."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from copy import copy
from typing import Any

import structlog

from app.core import AgentEvent, AgentEventType
from app.core.agent_engine import AgentEngine
from app.core.collaboration.constants import FALLBACK_MODELS, MAX_RETRIES, TASK_TIMEOUT
from app.core.collaboration.progress import get_progress_tracker, get_task_tree
from app.core.di import resolve as di_resolve
from app.core.group_ws_hub import group_ws_hub
from app.core.principal import LOCAL_SUBJECT_ID, Principal, get_context_principal

logger = structlog.get_logger(__name__)

# Cap for streamed event payloads pushed over the group WebSocket.
_MAX_AGENT_EVENT_CHARS = 2000

# Canonical protocol event for each agent engine event type.
_AGENT_EVENT_CANONICAL: dict[AgentEventType, str] = {
    AgentEventType.TEXT: "content_delta",
    AgentEventType.THINKING: "content_delta",
    AgentEventType.TOOL_CALL: "tool_result",
    AgentEventType.TOOL_RESULT: "tool_result",
    AgentEventType.DONE: "message_complete",
    AgentEventType.ERROR: "error",
}


def _truncate(value: Any) -> str:
    """Render a value as a bounded string for WS event payloads."""
    return str(value)[:_MAX_AGENT_EVENT_CHARS]


async def _broadcast_agent_event(group_id: str, role: str, agent_id: str, event: AgentEvent) -> None:
    """Mirror one agent engine event onto the group WS as a canonical event.

    Purely observational: never raises, so the agent run cannot be broken
    by broadcasting failures. Progress counters are recorded alongside so
    the sub-agent task tree can consume live progress.
    """
    try:
        canonical = _AGENT_EVENT_CANONICAL.get(event.type)
        if canonical is None:
            return
        tracker = get_progress_tracker(
            f"{group_id}:{agent_id}",
            group_id=group_id,
            agent_id=agent_id,
            role=role,
        )
        data: dict[str, Any] = {"role": role, "agent_id": agent_id}
        if event.type in (AgentEventType.TEXT, AgentEventType.THINKING):
            data["event"] = "thinking" if event.type == AgentEventType.THINKING else "text"
            data["content"] = _truncate(event.data.get("content", ""))
            tracker.record_activity(data["event"])
        elif event.type == AgentEventType.TOOL_CALL:
            data["event"] = "tool_call"
            data["tool_name"] = event.data.get("name", "")
            tracker.record_tool_call(data["tool_name"])
        elif event.type == AgentEventType.TOOL_RESULT:
            data["event"] = "tool_result"
            data["result"] = _truncate(event.data.get("result", ""))
            tracker.record_activity("tool_result")
        elif event.type == AgentEventType.DONE:
            data["event"] = "message_complete"
            data["tokens_used"] = event.data.get("tokens_used", 0)
            tracker.record_output_tokens(data["tokens_used"])
            tracker.record_activity("done")
        else:
            data["event"] = "agent_error"
            data["error"] = _truncate(event.data.get("error", "unknown_error"))
            tracker.record_activity("error")
        await group_ws_hub.broadcast_canonical(group_id, canonical, data)
    except Exception as exc:
        logger.warning("agent_event_broadcast_failed", group_id=group_id, agent_id=agent_id, error=str(exc))


async def _open_task_node(
    group_id: str,
    role: str,
    agent_id: str,
    task_name: str | None,
) -> tuple[Any, Any]:
    """Register a sub-agent turn as a node in the group task tree."""
    try:
        tree = get_task_tree(group_id, create=True)
        root = await tree.ensure_root(task_name or f"task:{group_id}")
        node = await tree.add_node(
            root.node_id,
            f"{role}:{agent_id}",
            metadata={"role": role, "agent_id": agent_id},
        )
    except Exception as exc:
        logger.warning("task_tree_node_open_failed", group_id=group_id, agent_id=agent_id, error=str(exc))
        return None, None
    return tree, node


async def _close_task_node(tree: Any, node: Any, status: str) -> None:
    """Mark a task tree node terminal; never raises."""
    if tree is None or node is None:
        return
    try:
        await tree.update_status(node.node_id, status)
    except Exception as exc:
        logger.warning("task_tree_node_close_failed", node_id=getattr(node, "node_id", ""), error=str(exc))


async def _ensure_task_root(group_id: str, task_name: str | None) -> None:
    """Ensure the group task tree root exists so turn nodes nest correctly."""
    try:
        tree = get_task_tree(group_id, create=True)
        await tree.ensure_root(task_name or f"task:{group_id}")
    except Exception as exc:
        logger.warning("task_tree_root_open_failed", group_id=group_id, error=str(exc))


def principal_for_group(group: Any) -> Principal:
    """Resolve the explicit execution principal for a group task.

    Group tasks execute with the group owner identity so background execution
    always carries an explicit principal and never depends on the
    request-scoped ``get_context_principal`` fallback (which raises RuntimeError
    when auth is enabled and no request context exists).

    Args:
        group: The group entity (or any object with a ``user_id`` attribute).

    Returns:
        A Principal carrying the group owner subject id.
    """
    owner = str(getattr(group, "user_id", "") or "").strip()
    return Principal(subject_id=owner or LOCAL_SUBJECT_ID)


async def run_agent(
    agent_id: str,
    provider: str,
    model_id: str,
    api_key: str,
    system_prompt: str,
    user_message: str,
    tools: list[str],
    base_url: str | None = None,
    principal: Principal | None = None,
    group_id: str | None = None,
    task_name: str | None = None,
) -> AsyncIterator[AgentEvent]:
    """Run a single agent turn and yield events.

    Args:
        agent_id: The agent ID.
        provider: The model provider.
        model_id: The model ID.
        api_key: The API key.
        system_prompt: The system prompt.
        user_message: The user message.
        tools: List of tool names.
        base_url: Optional base URL.
        principal: Optional principal for scoping.
        group_id: Optional collaboration group for cost attribution; stamped
            into the session context so CostRecord rows carry it (R12-H54).
        task_name: Optional sub-task id for cost attribution.

    Yields:
        AgentEvent instances from the agent engine.
    """
    # Keep provider constructors and registry behavior, but isolate role credentials.
    model_registry = copy(di_resolve("ModelRegistry"))
    model_registry._models = {}  # noqa: SLF001 - isolated copy of the existing registry
    model_registry._user_keys = {}  # noqa: SLF001 - never mutate the shared registry
    adapter = model_registry.register_model(model_id, provider, api_key, base_url)
    model_registry.get_default = lambda: adapter
    tool_registry = di_resolve("ToolRegistry")
    engine = AgentEngine(model_registry=model_registry, tool_registry=tool_registry)
    principal = principal or get_context_principal()
    session = engine.create_session(
        agent_id=agent_id,
        user_id=principal.subject_id,
        provider=provider,
        model_id=model_id,
        api_key=api_key,
        base_url=base_url,
        system_prompt=system_prompt,
        tools=tools,
    )
    if group_id or task_name:
        session.context["group_id"] = group_id
        session.context["task_id"] = task_name or f"task:{group_id}"
    async for event in engine.run(session, user_message):
        yield event


async def run_agent_simple(
    agent_id: str,
    provider: str,
    model_id: str,
    api_key: str,
    system_prompt: str,
    user_message: str,
    tools: list[str],
    base_url: str | None = None,
    principal: Principal | None = None,
    group_id: str | None = None,
    role: str = "worker",
    task_name: str | None = None,
) -> tuple[str, int]:
    """Run a single agent turn and return (output, tokens_used).

    Args:
        agent_id: The agent ID.
        provider: The model provider.
        model_id: The model ID.
        api_key: The API key.
        system_prompt: The system prompt.
        user_message: The user message.
        tools: List of tool names.
        base_url: Optional base URL.
        principal: Optional principal for scoping.
        group_id: Optional group ID. When provided, each engine event is
            mirrored onto the group WS as a canonical protocol event
            (content_delta / tool_result / message_complete / error),
            progress counters are recorded and the turn is registered as
            a task tree node that transitions running -> completed /
            failed / stopped.
        role: The agent role label used in broadcast payloads.
        task_name: Optional task name for the task tree root (defaults to
            ``task:group_id``); the turn node is named ``role:agent_id``.

    Returns:
        A tuple of (output_text, tokens_used) on DONE, including empty text
        for successful tool-only runs.

    Raises:
        RuntimeError: If the event stream ends without DONE.
        Exception: If the agent emits ERROR or raises during execution.
    """
    output = ""
    total_tokens = 0
    principal = principal or get_context_principal()
    tree, node = (None, None)
    if group_id:
        tree, node = await _open_task_node(group_id, role, agent_id, task_name)
    try:
        async for event in run_agent(
            agent_id,
            provider,
            model_id,
            api_key,
            system_prompt,
            user_message,
            tools,
            base_url,
            principal,
            group_id,
            task_name,
        ):
            if group_id:
                await _broadcast_agent_event(group_id, role, agent_id, event)
            if event.type == AgentEventType.TEXT:
                output += event.data.get("content", "")
            elif event.type == AgentEventType.TOOL_CALL:
                pass
            elif event.type == AgentEventType.DONE:
                total_tokens += event.data.get("tokens_used", 0)
                break
            elif event.type == AgentEventType.ERROR:
                raise Exception(event.data.get("error", "unknown_error"))
        else:
            raise RuntimeError("Agent event stream ended without DONE")
    except asyncio.CancelledError:
        await _close_task_node(tree, node, "stopped")
        raise
    except Exception:
        await _close_task_node(tree, node, "failed")
        raise
    await _close_task_node(tree, node, "completed")
    return output, total_tokens


async def run_agent_with_retry(
    agent_id: str,
    provider: str,
    model_id: str,
    api_key: str,
    system_prompt: str,
    user_message: str,
    tools: list[str],
    group_id: str,
    role: str = "worker",
    base_url: str | None = None,
    principal: Principal | None = None,
    task_name: str | None = None,
) -> tuple[str, int]:
    """Run agent with retry and fallback, returns (output, tokens_used).

    Wraps ``_run_agent_with_retry_impl`` (which owns retry, timeout,
    fallback and failure semantics) with sub-agent task tree observation:
    when ``group_id`` is provided the tree root is registered under
    ``task_name`` and every actual agent turn (each retry attempt and the
    fallback run) registers its own tree node that transitions
    running -> completed / failed / stopped inside ``run_agent_simple``,
    so live progress broadcasting and node lifecycle stay in one place.

    Args:
        agent_id: The agent ID.
        provider: The model provider.
        model_id: The model ID.
        api_key: The API key.
        system_prompt: The system prompt.
        user_message: The user message.
        tools: List of tool names.
        group_id: The group ID for broadcast notifications.
        role: The agent role for logging.
        base_url: Optional base URL.
        principal: Optional principal for scoping.
        task_name: Optional task name for the task tree root (defaults to
            ``task:group_id``); turn nodes are named ``role:agent_id``.

    Returns:
        A tuple of (output_text, tokens_used) after a successful DONE event,
        including empty text for tool-only runs.

    Raises:
        RuntimeError: If all attempts fail, chained from the last error.
        asyncio.CancelledError: If execution is cancelled; never retried.
    """
    if group_id:
        await _ensure_task_root(group_id, task_name)
    return await _run_agent_with_retry_impl(
        agent_id=agent_id,
        provider=provider,
        model_id=model_id,
        api_key=api_key,
        system_prompt=system_prompt,
        user_message=user_message,
        tools=tools,
        group_id=group_id,
        role=role,
        base_url=base_url,
        principal=principal,
        task_name=task_name,
    )


async def _run_agent_with_retry_impl(
    agent_id: str,
    provider: str,
    model_id: str,
    api_key: str,
    system_prompt: str,
    user_message: str,
    tools: list[str],
    group_id: str,
    role: str = "worker",
    base_url: str | None = None,
    principal: Principal | None = None,
    task_name: str | None = None,
) -> tuple[str, int]:
    """Run agent with retry and fallback (single source of truth).

    Args:
        agent_id: The agent ID.
        provider: The model provider.
        model_id: The model ID.
        api_key: The API key.
        system_prompt: The system prompt.
        user_message: The user message.
        tools: List of tool names.
        group_id: The group ID for broadcast notifications and progress.
        role: The agent role for logging and progress payloads.
        base_url: Optional base URL.
        principal: Optional principal for scoping.
        task_name: Optional task name forwarded to ``run_agent_simple`` for
            task tree root naming.

    Returns:
        A tuple of (output_text, tokens_used) after a successful DONE event,
        including empty text for tool-only runs.

    Raises:
        RuntimeError: If all attempts fail, chained from the last error.
        asyncio.CancelledError: If execution is cancelled; never retried.
    """
    last_error: Exception | None = None
    principal = principal or get_context_principal()

    for attempt in range(MAX_RETRIES + 1):
        try:
            async with asyncio.timeout(TASK_TIMEOUT):
                output, total_tokens = await run_agent_simple(
                    agent_id=agent_id,
                    provider=provider,
                    model_id=model_id,
                    api_key=api_key,
                    system_prompt=system_prompt,
                    user_message=user_message,
                    tools=tools,
                    base_url=base_url,
                    principal=principal,
                    group_id=group_id,
                    role=role,
                    task_name=task_name,
                )
            return output, total_tokens
        except TimeoutError as e:
            last_error = e
        except Exception as e:
            last_error = e

        if attempt < MAX_RETRIES:
            await group_ws_hub.broadcast(group_id, {
                "type": "system_message",
                "data": {"content": f"{role} 调用失败，正在重试 ({attempt + 1}/{MAX_RETRIES})..."},
            })

    return await _try_fallback_model(
        agent_id,
        provider,
        model_id,
        api_key,
        system_prompt,
        user_message,
        tools,
        group_id,
        role,
        base_url,
        last_error,
        principal,
        task_name,
    )


async def _try_fallback_model(
    agent_id: str,
    provider: str,
    model_id: str,
    api_key: str,
    system_prompt: str,
    user_message: str,
    tools: list[str],
    group_id: str,
    role: str,
    base_url: str | None,
    last_error: Exception | None,
    principal: Principal,
    task_name: str | None = None,
) -> tuple[str, int]:
    """Attempt to run agent with a fallback (degraded) model.

    Args:
        agent_id: The agent ID.
        provider: The original provider.
        model_id: The original model ID.
        api_key: The API key.
        system_prompt: The system prompt.
        user_message: The user message.
        tools: List of tool names.
        group_id: The group ID for broadcast and progress.
        role: The agent role for logging and progress payloads.
        base_url: Optional base URL.
        last_error: The last error from primary attempts.
        principal: The explicit execution principal.
        task_name: Optional task name forwarded to ``run_agent_simple`` for
            task tree root naming.

    Returns:
        A tuple of (output_text, tokens_used) after a successful DONE event,
        including empty text for tool-only runs.

    Raises:
        RuntimeError: If fallback fails or is unavailable, chained from the
            last fallback or primary error.
        asyncio.CancelledError: If fallback execution is cancelled.
    """
    fallback = _get_fallback_model(provider, model_id)
    if fallback:
        fb_provider, fb_model = fallback
        await group_ws_hub.broadcast(group_id, {
            "type": "system_message",
            "data": {"content": f"正在降级到 {fb_model}..."},
        })
        try:
            async with asyncio.timeout(TASK_TIMEOUT):
                output, total_tokens = await run_agent_simple(
                    agent_id=agent_id,
                    provider=fb_provider,
                    model_id=fb_model,
                    api_key=api_key,
                    system_prompt=system_prompt,
                    user_message=user_message,
                    tools=tools,
                    base_url=base_url,
                    principal=principal,
                    group_id=group_id,
                    role=role,
                    task_name=task_name,
                )
            return output, total_tokens
        except Exception as e:
            last_error = e

    logger.error(f"{role}_failed_after_retry", agent_id=agent_id, error=str(last_error) if last_error else "unknown")
    raise RuntimeError(f"{role} failed after retry") from last_error


def _get_fallback_model(provider: str, model_id: str) -> tuple[str, str] | None:
    """Get fallback model for degradation.

    Args:
        provider: The current provider.
        model_id: The current model ID.

    Returns:
        A tuple of (fallback_provider, fallback_model) or None.
    """
    key = model_id.lower()
    if key in FALLBACK_MODELS:
        return FALLBACK_MODELS[key]
    from app.models.registry import MODEL_ALIASES
    if key in MODEL_ALIASES:
        resolved_provider, resolved_model = MODEL_ALIASES[key]
        if resolved_model.lower() in FALLBACK_MODELS:
            return FALLBACK_MODELS[resolved_model.lower()]
    return None
