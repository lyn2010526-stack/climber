"""Agent execution with retry and fallback for group collaboration."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import structlog

from app.core import AgentEvent, AgentEventType
from app.core.agent_engine import AgentEngine
from app.core.collaboration.constants import FALLBACK_MODELS, MAX_RETRIES, TASK_TIMEOUT
from app.core.di import resolve as di_resolve
from app.core.group_ws_hub import group_ws_hub
from app.core.principal import Principal, get_context_principal

logger = structlog.get_logger(__name__)


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

    Yields:
        AgentEvent instances from the agent engine.
    """
    model_registry = di_resolve("ModelRegistry")
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

    Returns:
        A tuple of (output_text, tokens_used).
    """
    output = ""
    total_tokens = 0
    principal = principal or get_context_principal()
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
    ):
        if event.type == AgentEventType.TEXT:
            output += event.data.get("content", "")
        elif event.type == AgentEventType.TOOL_CALL:
            pass
        elif event.type == AgentEventType.DONE:
            total_tokens += event.data.get("tokens_used", 0)
            break
        elif event.type == AgentEventType.ERROR:
            raise Exception(event.data.get("error", "unknown_error"))
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
) -> tuple[str, int]:
    """Run agent with retry and fallback, returns (output, tokens_used).

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

    Returns:
        A tuple of (output_text, tokens_used), or ("", 0) on failure.
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
                )
            if output or not last_error:
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
        group_id: The group ID for broadcast.
        role: The agent role.
        base_url: Optional base URL.
        last_error: The last error from primary attempts.

    Returns:
        A tuple of (output_text, tokens_used), or ("", 0) on failure.
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
                )
            if output:
                return output, total_tokens
        except Exception:
            pass

    logger.error(f"{role}_failed_after_retry", agent_id=agent_id, error=str(last_error) if last_error else "unknown")
    return "", 0


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
