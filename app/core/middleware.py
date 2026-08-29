"""Middleware system for the Agent Engine.

Provides composable hooks at key execution points in the agent lifecycle,
inspired by AgentScope's middleware architecture.

Hook points (onion pattern with before/after):
- on_reasoning: Intercepts the LLM call phase
- on_acting: Intercepts tool execution
- on_compress_context: Intercepts context compression
- on_check_permission: Intercepts permission checking

Transformer pattern:
- on_system_prompt: Transforms the system prompt string
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Callable
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from app.core.agent_engine import AgentEngine, AgentSession

logger = structlog.get_logger()


class MiddlewareBase:
    """Base class for all middleware implementations.

    Each hook is optional - only implement the ones you need.
    The middleware chain detects which hooks are implemented at runtime.

    Example::

        class LoggingMiddleware(MiddlewareBase):
            async def on_reasoning(self, engine, session, input_kwargs, next_handler):
                logger.info("Before reasoning")
                async for event in next_handler():
                    yield event
                logger.info("After reasoning")
    """

    def is_implemented(self, hook_name: str) -> bool:
        """Check if a hook method is overridden in the subclass."""
        base_method = getattr(MiddlewareBase, hook_name, None)
        sub_method = getattr(type(self), hook_name, None)
        return base_method is not sub_method

    async def on_reasoning(
        self,
        engine: AgentEngine,
        session: AgentSession,
        input_kwargs: dict[str, Any],
        next_handler: Callable[..., AsyncGenerator],
    ) -> AsyncGenerator:
        """Hook for intercepting the reasoning/LLM call phase.

        Args:
            engine: The AgentEngine instance
            session: The current agent session
            input_kwargs: Dict with keys like 'messages', 'tools', 'adapter'
            next_handler: Callable that executes next middleware or original

        Yields:
            AgentEvent objects from the reasoning process
        """
        raise RuntimeError(f"{type(self).__name__} does not implement on_reasoning")
        yield  # pragma: no cover

    async def on_acting(
        self,
        engine: AgentEngine,
        session: AgentSession,
        input_kwargs: dict[str, Any],
        next_handler: Callable[..., AsyncGenerator],
    ) -> AsyncGenerator:
        """Hook for intercepting tool execution.

        Args:
            engine: The AgentEngine instance
            session: The current agent session
            input_kwargs: Dict with keys like 'tool_calls', 'executor'
            next_handler: Callable that executes next middleware or original

        Yields:
            AgentEvent objects from tool execution
        """
        raise RuntimeError(f"{type(self).__name__} does not implement on_acting")
        yield  # pragma: no cover

    async def on_compress_context(
        self,
        engine: AgentEngine,
        session: AgentSession,
        input_kwargs: dict[str, Any],
        next_handler: Callable[..., asyncio.coroutine],
    ) -> None:
        """Hook for intercepting context compression.

        Args:
            engine: The AgentEngine instance
            session: The current agent session
            input_kwargs: Dict with keys like 'ctx_tokens', 'ctx_limit'
            next_handler: Callable that executes next middleware or original
        """
        raise RuntimeError(f"{type(self).__name__} does not implement on_compress_context")

    async def on_check_permission(
        self,
        engine: AgentEngine,
        session: AgentSession,
        input_kwargs: dict[str, Any],
        next_handler: Callable[..., Any],
    ) -> tuple[bool, str]:
        """Hook for intercepting permission checking.

        Args:
            engine: The AgentEngine instance
            session: The current agent session
            input_kwargs: Dict with keys like 'tool_name', 'arguments'
            next_handler: Callable that executes next middleware or original

        Returns:
            Tuple of (allowed, reason)
        """
        raise RuntimeError(f"{type(self).__name__} does not implement on_check_permission")

    async def on_system_prompt(
        self,
        engine: AgentEngine,
        session: AgentSession,
        current_prompt: str,
    ) -> str:
        """Transform the system prompt string (pipeline pattern).

        Args:
            engine: The AgentEngine instance
            session: The current agent session
            current_prompt: The current system prompt

        Returns:
            Transformed system prompt
        """
        raise RuntimeError(f"{type(self).__name__} does not implement on_system_prompt")


class MiddlewareChain:
    """Executes a chain of middlewares for a given hook point.

    Uses onion pattern (before/after) for most hooks,
    and pipeline pattern for system_prompt transformation.
    """

    def __init__(self, middlewares: list[MiddlewareBase] | None = None):
        self._middlewares = middlewares or []
        # Pre-filter middlewares by implemented hooks
        self._reasoning = [m for m in self._middlewares if m.is_implemented("on_reasoning")]
        self._acting = [m for m in self._middlewares if m.is_implemented("on_acting")]
        self._compress = [m for m in self._middlewares if m.is_implemented("on_compress_context")]
        self._permission = [m for m in self._middlewares if m.is_implemented("on_check_permission")]
        self._system_prompt = [m for m in self._middlewares if m.is_implemented("on_system_prompt")]

    @property
    def has_reasoning_middleware(self) -> bool:
        return len(self._reasoning) > 0

    @property
    def has_acting_middleware(self) -> bool:
        return len(self._acting) > 0

    @property
    def has_compress_middleware(self) -> bool:
        return len(self._compress) > 0

    @property
    def has_permission_middleware(self) -> bool:
        return len(self._permission) > 0

    @property
    def has_system_prompt_middleware(self) -> bool:
        return len(self._system_prompt) > 0

    async def execute_reasoning(
        self,
        engine: AgentEngine,
        session: AgentSession,
        input_kwargs: dict[str, Any],
        original_handler: Callable[..., AsyncGenerator],
    ) -> AsyncGenerator:
        """Execute the reasoning middleware chain."""
        if not self._reasoning:
            async for event in original_handler():
                yield event
            return

        async def chain(index: int = 0) -> AsyncGenerator:
            if index >= len(self._reasoning):
                async for event in original_handler():
                    yield event
            else:
                mw = self._reasoning[index]
                async def next_handler(**kwargs):
                    input_kwargs.update(kwargs)
                    async for event in chain(index + 1):
                        yield event
                async for event in mw.on_reasoning(engine, session, input_kwargs, next_handler):
                    yield event

        async for event in chain():
            yield event

    async def execute_acting(
        self,
        engine: AgentEngine,
        session: AgentSession,
        input_kwargs: dict[str, Any],
        original_handler: Callable[..., AsyncGenerator],
    ) -> AsyncGenerator:
        """Execute the acting middleware chain."""
        if not self._acting:
            async for event in original_handler():
                yield event
            return

        async def chain(index: int = 0) -> AsyncGenerator:
            if index >= len(self._acting):
                async for event in original_handler():
                    yield event
            else:
                mw = self._acting[index]
                async def next_handler(**kwargs):
                    input_kwargs.update(kwargs)
                    async for event in chain(index + 1):
                        yield event
                async for event in mw.on_acting(engine, session, input_kwargs, next_handler):
                    yield event

        async for event in chain():
            yield event

    async def execute_compress(
        self,
        engine: AgentEngine,
        session: AgentSession,
        input_kwargs: dict[str, Any],
        original_handler: Callable[..., Any],
    ) -> None:
        """Execute the compress_context middleware chain."""
        if not self._compress:
            await original_handler()
            return

        async def chain(index: int = 0) -> None:
            if index >= len(self._compress):
                await original_handler()
            else:
                mw = self._compress[index]
                async def next_handler(**kwargs):
                    input_kwargs.update(kwargs)
                    await chain(index + 1)
                await mw.on_compress_context(engine, session, input_kwargs, next_handler)

        await chain()

    async def execute_permission(
        self,
        engine: AgentEngine,
        session: AgentSession,
        input_kwargs: dict[str, Any],
        original_handler: Callable[..., Any],
    ) -> tuple[bool, str]:
        """Execute the permission middleware chain."""
        if not self._permission:
            return await original_handler()

        async def chain(index: int = 0) -> tuple[bool, str]:
            if index >= len(self._permission):
                return await original_handler()
            mw = self._permission[index]
            async def next_handler(**kwargs):
                input_kwargs.update(kwargs)
                return await chain(index + 1)
            return await mw.on_check_permission(engine, session, input_kwargs, next_handler)

        return await chain()

    async def transform_system_prompt(
        self,
        engine: AgentEngine,
        session: AgentSession,
        prompt: str,
    ) -> str:
        """Execute the system prompt transformation pipeline."""
        result = prompt
        for mw in self._system_prompt:
            result = await mw.on_system_prompt(engine, session, result)
        return result
