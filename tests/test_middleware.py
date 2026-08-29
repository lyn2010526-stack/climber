"""Tests for the middleware system (AgentScope-inspired)."""

from unittest.mock import MagicMock

import pytest

from app.core.middleware import MiddlewareBase, MiddlewareChain


class RecordingMiddleware(MiddlewareBase):
    """Test middleware that records hook invocations."""

    def __init__(self, name: str = "test"):
        self.name = name
        self.calls: list[str] = []

    async def on_reasoning(self, engine, session, input_kwargs, next_handler):
        self.calls.append("reasoning:before")
        async for event in next_handler():
            yield event
        self.calls.append("reasoning:after")

    async def on_acting(self, engine, session, input_kwargs, next_handler):
        self.calls.append("acting:before")
        async for event in next_handler():
            yield event
        self.calls.append("acting:after")

    async def on_compress_context(self, engine, session, input_kwargs, next_handler):
        self.calls.append("compress:before")
        await next_handler()
        self.calls.append("compress:after")

    async def on_check_permission(self, engine, session, input_kwargs, next_handler):
        self.calls.append("permission:before")
        result = await next_handler()
        self.calls.append("permission:after")
        return result

    async def on_system_prompt(self, engine, session, current_prompt):
        self.calls.append("system_prompt")
        return f"[{self.name}] {current_prompt}"


class BlockingPermissionMiddleware(MiddlewareBase):
    """Test middleware that blocks all tool calls."""

    async def on_check_permission(self, engine, session, input_kwargs, next_handler):
        return False, "blocked by test middleware"


class TestMiddlewareBase:
    def test_is_implemented_returns_false_for_base(self):
        mw = MiddlewareBase()
        assert mw.is_implemented("on_reasoning") is False
        assert mw.is_implemented("on_acting") is False

    def test_is_implemented_returns_true_for_override(self):
        mw = RecordingMiddleware()
        assert mw.is_implemented("on_reasoning") is True
        assert mw.is_implemented("on_acting") is True
        assert mw.is_implemented("on_compress_context") is True
        assert mw.is_implemented("on_check_permission") is True
        assert mw.is_implemented("on_system_prompt") is True


class TestMiddlewareChain:
    def test_empty_chain(self):
        chain = MiddlewareChain([])
        assert chain.has_reasoning_middleware is False
        assert chain.has_acting_middleware is False
        assert chain.has_compress_middleware is False
        assert chain.has_permission_middleware is False
        assert chain.has_system_prompt_middleware is False

    def test_chain_filters_middlewares(self):
        mw1 = RecordingMiddleware("mw1")
        mw2 = BlockingPermissionMiddleware()
        chain = MiddlewareChain([mw1, mw2])
        assert chain.has_reasoning_middleware is True
        assert chain.has_permission_middleware is True

    @pytest.mark.asyncio
    async def test_execute_system_prompt_pipeline(self):
        mw1 = RecordingMiddleware("first")
        mw2 = RecordingMiddleware("second")
        chain = MiddlewareChain([mw1, mw2])

        engine = MagicMock()
        session = MagicMock()

        result = await chain.transform_system_prompt(engine, session, "hello")
        assert result == "[second] [first] hello"
        assert mw1.calls == ["system_prompt"]
        assert mw2.calls == ["system_prompt"]

    @pytest.mark.asyncio
    async def test_execute_permission_chain_with_blocking(self):
        mw = BlockingPermissionMiddleware()
        chain = MiddlewareChain([mw])

        engine = MagicMock()
        session = MagicMock()

        async def original():
            return True, "original"

        allowed, reason = await chain.execute_permission(engine, session, {}, original)
        assert allowed is False
        assert reason == "blocked by test middleware"

    @pytest.mark.asyncio
    async def test_execute_reasoning_chain(self):
        mw = RecordingMiddleware()
        chain = MiddlewareChain([mw])

        engine = MagicMock()
        session = MagicMock()
        events_received = []

        async def original():
            yield "event1"
            yield "event2"

        async for event in chain.execute_reasoning(engine, session, {}, original):
            events_received.append(event)

        assert events_received == ["event1", "event2"]
        assert mw.calls == ["reasoning:before", "reasoning:after"]

    @pytest.mark.asyncio
    async def test_execute_acting_chain(self):
        mw = RecordingMiddleware()
        chain = MiddlewareChain([mw])

        engine = MagicMock()
        session = MagicMock()
        events_received = []

        async def original():
            yield "tool_result"

        async for event in chain.execute_acting(engine, session, {}, original):
            events_received.append(event)

        assert events_received == ["tool_result"]
        assert mw.calls == ["acting:before", "acting:after"]

    @pytest.mark.asyncio
    async def test_execute_compress_chain(self):
        mw = RecordingMiddleware()
        chain = MiddlewareChain([mw])

        engine = MagicMock()
        session = MagicMock()
        called = []

        async def original():
            called.append("compressed")

        await chain.execute_compress(engine, session, {}, original)
        assert called == ["compressed"]
        assert mw.calls == ["compress:before", "compress:after"]

    @pytest.mark.asyncio
    async def test_multiple_middlewares_execute_in_order(self):
        mw1 = RecordingMiddleware("first")
        mw2 = RecordingMiddleware("second")
        chain = MiddlewareChain([mw1, mw2])

        engine = MagicMock()
        session = MagicMock()

        result = await chain.transform_system_prompt(engine, session, "prompt")
        assert result == "[second] [first] prompt"
