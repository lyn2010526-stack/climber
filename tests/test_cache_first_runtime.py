"""Cache-first runtime contract and AgentEngine integration tests."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.core import ChatResult
from app.core.agent_engine import AgentEngine
from app.core.long_context.cache_first import CacheFirstRuntime, CacheRequest
from app.core.long_context.prefix_cache import PrefixCache
from app.core.middleware import MiddlewareBase
from app.middleware.metrics import CACHE_REQUEST_TOTAL, CACHE_TOKEN_TOTAL
from app.models import ModelCapability
from app.models.registry import ModelRegistry
from app.tools import ToolRegistry


def _request(**overrides) -> CacheRequest:
    values = {
        "messages": [{"role": "system", "content": "fixed"}, {"role": "user", "content": "hello"}],
        "tools": [{"type": "function", "function": {"name": "read", "parameters": {"type": "object"}}}],
        "provider": "test-provider",
        "model_id": "test-model",
        "parameters": {"temperature": 0.2},
    }
    values.update(overrides)
    return CacheRequest.from_call(**values)


def test_cache_key_includes_prefix_tools_model_and_parameters():
    base = _request()

    assert _request(messages=[{"role": "system", "content": "revised"}]).key != base.key
    assert _request(tools=[]).key != base.key
    assert _request(model_id="other-model").key != base.key
    assert _request(parameters={"temperature": 0.8}).key != base.key


@pytest.mark.asyncio
async def test_runtime_singleflight_prevents_stampede_and_replays_complete_result():
    runtime = CacheFirstRuntime(PrefixCache())
    calls = 0

    async def produce() -> ChatResult:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return ChatResult(content="complete", finish_reason="stop", tokens_used=9)

    first, second = await asyncio.gather(
        runtime.run(_request(), produce),
        runtime.run(_request(), produce),
    )
    replay = await runtime.run(_request(), produce)

    assert calls == 1
    assert first.content == second.content == replay.content == "complete"
    assert first.cache_hit is False
    assert second.cache_hit is True
    assert replay.cache_hit is True


@pytest.mark.asyncio
async def test_runtime_cancelled_follower_does_not_cancel_shared_flight():
    runtime = CacheFirstRuntime(PrefixCache())
    producer_started = asyncio.Event()
    release_producer = asyncio.Event()
    calls = 0

    async def produce() -> ChatResult:
        nonlocal calls
        calls += 1
        producer_started.set()
        await release_producer.wait()
        return ChatResult(content="complete", finish_reason="stop")

    owner = asyncio.create_task(runtime.run(_request(), produce))
    await producer_started.wait()
    follower = asyncio.create_task(runtime.run(_request(), produce))
    await asyncio.sleep(0)
    follower.cancel()
    with pytest.raises(asyncio.CancelledError):
        await follower

    release_producer.set()
    result = await owner
    replay = await runtime.run(_request(), produce)

    assert result.content == replay.content == "complete"
    assert calls == 1
    assert replay.cache_hit is True


@pytest.mark.asyncio
async def test_runtime_cancelled_owner_does_not_cancel_shared_flight():
    runtime = CacheFirstRuntime(PrefixCache())
    producer_started = asyncio.Event()
    release_producer = asyncio.Event()
    calls = 0

    async def produce() -> ChatResult:
        nonlocal calls
        calls += 1
        producer_started.set()
        await release_producer.wait()
        return ChatResult(content="complete", finish_reason="stop")

    owner = asyncio.create_task(runtime.run(_request(), produce))
    await producer_started.wait()
    follower = asyncio.create_task(runtime.run(_request(), produce))
    await asyncio.sleep(0)

    owner.cancel()
    with pytest.raises(asyncio.CancelledError):
        await owner

    release_producer.set()
    result = await follower

    assert result.content == "complete"
    assert calls == 1


@pytest.mark.asyncio
async def test_runtime_cancelled_only_waiter_allows_flight_to_finish_and_cache():
    runtime = CacheFirstRuntime(PrefixCache())
    producer_started = asyncio.Event()
    release_producer = asyncio.Event()
    producer_finished = asyncio.Event()
    calls = 0

    async def produce() -> ChatResult:
        nonlocal calls
        calls += 1
        producer_started.set()
        await release_producer.wait()
        producer_finished.set()
        return ChatResult(content="complete", finish_reason="stop")

    owner = asyncio.create_task(runtime.run(_request(), produce))
    await producer_started.wait()
    owner.cancel()
    with pytest.raises(asyncio.CancelledError):
        await owner

    release_producer.set()
    await producer_finished.wait()
    await asyncio.sleep(0)
    replay = await runtime.run(_request(), produce)

    assert calls == 1
    assert replay.cache_hit is True


@pytest.mark.asyncio
async def test_runtime_failed_flight_is_removed_before_retry():
    runtime = CacheFirstRuntime(PrefixCache())
    calls = 0

    async def produce() -> ChatResult:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("provider failed")
        return ChatResult(content="recovered", finish_reason="stop")

    with pytest.raises(RuntimeError, match="provider failed"):
        await runtime.run(_request(), produce)

    result = await runtime.run(_request(), produce)

    assert calls == 2
    assert result.content == "recovered"


@pytest.mark.asyncio
async def test_runtime_bounds_background_flights_and_bypasses_overflow():
    runtime = CacheFirstRuntime(PrefixCache(), max_flights=1)
    first_started = asyncio.Event()
    release_first = asyncio.Event()

    async def produce_first() -> ChatResult:
        first_started.set()
        await release_first.wait()
        return ChatResult(content="first", finish_reason="stop")

    first = asyncio.create_task(runtime.run(_request(), produce_first))
    await first_started.wait()
    overflow = await runtime.run(
        _request(messages=[{"role": "user", "content": "overflow"}]),
        AsyncMock(return_value=ChatResult(content="overflow", finish_reason="stop")),
    )

    assert overflow.content == "overflow"
    assert len(runtime._flights) == 1
    assert runtime.cache.lookup(
        _request(messages=[{"role": "user", "content": "overflow"}]).key
    ) is None

    release_first.set()
    await first


@pytest.mark.asyncio
async def test_cache_hits_increment_request_and_token_metrics():
    runtime = CacheFirstRuntime(PrefixCache())
    request = _request(model_id="metrics-model")
    hit_counter = CACHE_REQUEST_TOTAL.labels(result="hit")
    token_counter = CACHE_TOKEN_TOTAL.labels(
        provider=request.provider,
        model_id=request.model_id,
        type="hit",
    )
    hits_before = hit_counter._value.get()
    tokens_before = token_counter._value.get()

    await runtime.run(
        request,
        AsyncMock(return_value=ChatResult(content="complete", finish_reason="stop")),
    )
    await runtime.run(request, AsyncMock())

    assert hit_counter._value.get() == hits_before + 1
    assert token_counter._value.get() == tokens_before + request.input_tokens


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "result,cancelled",
    [
        (ChatResult(content="", tool_calls=[{"id": "call"}], finish_reason="tool_calls"), False),
        (ChatResult(content="error", finish_reason="error"), False),
        (ChatResult(content="partial", finish_reason=None), False),
        (ChatResult(content="cancelled", finish_reason="stop"), True),
    ],
)
async def test_runtime_only_writes_complete_clean_uncancelled_results(result, cancelled):
    cache = PrefixCache()
    runtime = CacheFirstRuntime(cache)

    await runtime.run(_request(), AsyncMock(return_value=result), cancelled=lambda: cancelled)

    assert cache.entries == ()


class _Memory:
    async def format_memories_for_prompt(self, **kwargs):
        return ""

    async def store_memory(self, **kwargs):
        return None


class _NonStreamingAdapter:
    provider = "fake"
    model_id = "cache-model"
    capabilities = ModelCapability(streaming=False, max_tokens=4096)

    def __init__(self, content: str = "raw secret"):
        self.calls = 0
        self.content = content

    async def chat(self, messages, tools=None, **kwargs):
        self.calls += 1
        return ChatResult(content=self.content, finish_reason="stop", tokens_used=8)


class _StreamingAdapter:
    provider = "fake"
    model_id = "stream-cache-model"
    capabilities = ModelCapability(streaming=True, max_tokens=4096)

    def __init__(self):
        self.calls = 0

    async def stream_chat(self, messages, tools=None, **kwargs):
        self.calls += 1
        for content in ("stream", "ed"):
            yield type(
                "Chunk",
                (),
                {"content": content, "tool_calls": [], "usage": 8, "tokens_used": 0},
            )()


class _PassthroughReasoningMiddleware(MiddlewareBase):
    async def on_reasoning(self, engine, session, input_kwargs, next_handler):
        async for event in next_handler():
            yield event


@pytest.mark.asyncio
async def test_agent_engine_rejects_xml_tool_calls_before_cache_write(monkeypatch):
    registry = ModelRegistry()
    adapter = _NonStreamingAdapter('<function=read>{"path":"a"}</read>')
    registry._models["fake:cache-model"] = adapter
    engine = AgentEngine(model_registry=registry, tool_registry=ToolRegistry())
    session = engine.create_session("agent", "user", "fake", "cache-model", "key")

    from app.config import settings

    monkeypatch.setattr(settings, "enable_guardrails", False)
    result = await engine._chat_cache_first(adapter, session, [], None)

    assert result.tool_calls[0]["function"]["name"] == "read"
    assert engine.cache_first.cache.entries == ()


@pytest.mark.asyncio
async def test_agent_engine_non_streaming_main_path_replays_sanitized_cache(monkeypatch):
    registry = ModelRegistry()
    adapter = _NonStreamingAdapter()
    registry._models["fake:cache-model"] = adapter
    engine = AgentEngine(model_registry=registry, tool_registry=ToolRegistry())
    engine.debug_loop = None
    engine.memory_service = _Memory()
    engine._persist_message = AsyncMock()

    from app.config import settings
    from app.core.guardrails import default_guardrails

    monkeypatch.setattr(settings, "enable_guardrails", True)

    async def sanitize(content, *, is_input):
        if is_input:
            return content, []
        return "sanitized", [type("Violation", (), {"rule_name": "test"})()]

    monkeypatch.setattr(default_guardrails, "apply_guardrails", sanitize)

    first = engine.create_session("agent", "user", "fake", "cache-model", "key", system_prompt="fixed")
    second = engine.create_session("agent", "user", "fake", "cache-model", "key", system_prompt="fixed")
    first_result = await engine.run_agent(first, "same request")
    second_result = await engine.run_agent(second, "same request")

    assert first_result == {"output": "sanitized"}
    assert second_result == {"output": "sanitized"}
    assert adapter.calls == 1
    assert len(engine.cache_first.cache.entries) == 1
    assert engine.cache_first.cache.entries[0].value.content == "sanitized"
    assert engine.cache_first.cache.entries[0].value.cache_hit is False

    other_credential = engine.create_session(
        "agent", "user", "fake", "cache-model", "other-key", system_prompt="fixed"
    )
    assert await engine.run_agent(other_credential, "same request") == {"output": "sanitized"}
    assert adapter.calls == 2


@pytest.mark.asyncio
async def test_agent_engine_streaming_main_path_replays_cache(monkeypatch):
    registry = ModelRegistry()
    adapter = _StreamingAdapter()
    registry._models["fake:stream-cache-model"] = adapter
    engine = AgentEngine(model_registry=registry, tool_registry=ToolRegistry())
    engine.debug_loop = None
    engine.memory_service = _Memory()
    engine._persist_message = AsyncMock()

    from app.config import settings

    monkeypatch.setattr(settings, "enable_guardrails", False)
    first = engine.create_session("agent", "user", "fake", "stream-cache-model", "key", system_prompt="fixed")
    second = engine.create_session("agent", "user", "fake", "stream-cache-model", "key", system_prompt="fixed")

    first_result = await engine.run_agent(first, "same request")
    second_result = await engine.run_agent(second, "same request")

    assert first_result == {"output": "streamed"}
    assert second_result == {"output": "streamed"}
    assert adapter.calls == 1
    assert len(engine.cache_first.cache.entries) == 1


@pytest.mark.asyncio
async def test_agent_engine_stream_cache_miss_preserves_chunk_boundaries(monkeypatch):
    registry = ModelRegistry()
    adapter = _StreamingAdapter()
    registry._models["fake:stream-cache-model"] = adapter
    engine = AgentEngine(model_registry=registry, tool_registry=ToolRegistry())
    session = engine.create_session("agent", "user", "fake", "stream-cache-model", "key")

    from app.config import settings

    monkeypatch.setattr(settings, "enable_guardrails", False)
    result, events = await engine._stream_cache_first(adapter, session, [], None)

    assert result.content == "streamed"
    assert [content for content, _tool_calls in events] == ["stream", "ed"]


@pytest.mark.asyncio
async def test_agent_engine_reasoning_middleware_path_replays_cache(monkeypatch):
    registry = ModelRegistry()
    adapter = _NonStreamingAdapter(content="middleware result")
    registry._models["fake:cache-model"] = adapter
    engine = AgentEngine(
        model_registry=registry,
        tool_registry=ToolRegistry(),
        middlewares=[_PassthroughReasoningMiddleware()],
    )
    engine.debug_loop = None
    engine.memory_service = _Memory()
    engine._persist_message = AsyncMock()

    from app.config import settings

    monkeypatch.setattr(settings, "enable_guardrails", False)
    first = engine.create_session("agent", "user", "fake", "cache-model", "key", system_prompt="fixed")
    second = engine.create_session("agent", "user", "fake", "cache-model", "key", system_prompt="fixed")

    assert await engine.run_agent(first, "same request") == {"output": "middleware result"}
    assert await engine.run_agent(second, "same request") == {"output": "middleware result"}
    assert adapter.calls == 1
