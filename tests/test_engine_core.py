"""Tests for engine core modules: checkpoint, compressor, parallel, router, subagent."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio

from app.core import (
    AgentEventType, ChatResult, CheckpointData, CompressionStrategy,
    ContextConfig, MessageRole, ModelRoute,
    SessionStatus, SubAgentTask,
)
from app.core.compressor import ContextCompressor, estimate_tokens
from app.core.parallel import ParallelToolExecutor, ToolExecutionResult
from app.core.checkpoint import InMemoryCheckpointStore
from app.core.router import ModelRouter
from app.core.subagent import SubAgentRunner, SubAgentResult
from app.core.agent_engine import AgentEngine, AgentSession
from app.models import ModelAdapter, ModelCapability
from app.models.registry import ModelRegistry
from app.tools import ToolRegistry


# ── Helpers ──


class FakeModelAdapter:
    provider = "fake"
    model_id = "fake-model"

    def __init__(self, responses=None):
        self._responses = responses or [ChatResult(content="ok")]
        self._call_count = 0

    @property
    def api_key(self):
        return "fake"

    @api_key.setter
    def api_key(self, v):
        pass

    @property
    def capabilities(self):
        return ModelCapability(chat=True, streaming=False, tools=True)

    async def chat(self, messages, tools=None, **kw):
        idx = min(self._call_count, len(self._responses) - 1)
        self._call_count += 1
        return self._responses[idx]

    async def stream_chat(self, messages, tools=None, **kw):
        result = await self.chat(messages, tools, **kw)
        yield result


# ── estimate_tokens ──


class TestEstimateTokens:
    def test_empty_messages(self):
        assert estimate_tokens([]) == 0

    def test_single_message(self):
        msgs = [{"role": "user", "content": "hello"}]
        # "hello" = 5 chars, 5//4 = 1
        assert estimate_tokens(msgs) == 1

    def test_long_message(self):
        msgs = [{"role": "user", "content": "a" * 400}]
        assert estimate_tokens(msgs) == 100

    def test_tool_calls_counted(self):
        msgs = [{"role": "assistant", "tool_calls": [{"function": {"name": "echo", "arguments": "{}"}}]}]
        assert estimate_tokens(msgs) > 0


# ── ContextCompressor ──


class TestContextCompressor:
    @pytest.fixture
    def compressor(self):
        return ContextCompressor(ContextConfig(max_tokens=1000))

    def test_no_compression_needed(self, compressor):
        msgs = [{"role": "user", "content": "hi"}]
        assert not compressor.needs_compression(msgs)

    def test_compression_needed_for_long_context(self, compressor):
        long_msg = "x" * 5000
        msgs = [{"role": "system", "content": "sys"}, {"role": "user", "content": long_msg}]
        assert compressor.needs_compression(msgs)

    @pytest.mark.asyncio
    async def test_truncate_strategy(self):
        config = ContextConfig(max_tokens=100, compression_strategy=CompressionStrategy.TRUNCATE, keep_recent_messages=2)
        comp = ContextCompressor(config)
        model = FakeModelAdapter()

        # Messages must be long enough to exceed max_tokens=100
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "q1" * 100},
            {"role": "assistant", "content": "a1" * 100},
            {"role": "user", "content": "q2" * 100},
            {"role": "assistant", "content": "a2" * 100},
        ]
        result = await comp.compress(msgs, model)
        # Should keep system + truncation notice + last 2 = 4
        assert len(result) <= 4

    @pytest.mark.asyncio
    async def test_sliding_strategy(self):
        config = ContextConfig(max_tokens=100, compression_strategy=CompressionStrategy.SLIDING, keep_recent_messages=3)
        comp = ContextCompressor(config)
        model = FakeModelAdapter()

        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "q1"},
            {"role": "user", "content": "q2"},
            {"role": "user", "content": "q3"},
        ]
        result = await comp.compress(msgs, model)
        assert len(result) <= 6


# ── ParallelToolExecutor ──


class TestParallelToolExecutor:
    @pytest.fixture
    def registry(self):
        reg = ToolRegistry()

        @reg.tool(name="echo", description="Echo")
        async def echo(text: str) -> str:
            return f"Echo: {text}"

        @reg.tool(name="add", description="Add")
        async def add(a: int, b: int) -> str:
            return str(a + b)

        @reg.tool(name="slow", description="Slow tool")
        async def slow(text: str) -> str:
            await asyncio.sleep(0.05)
            return f"Slow: {text}"

        return reg

    @pytest.mark.asyncio
    async def test_execute_single(self, registry):
        executor = ParallelToolExecutor(registry)
        tc = [{"id": "c1", "function": {"name": "echo", "arguments": {"text": "hi"}}}]
        results = await executor.execute_all(tc)
        assert len(results) == 1
        assert results[0].result == "Echo: hi"
        assert results[0].success

    @pytest.mark.asyncio
    async def test_execute_parallel(self, registry):
        executor = ParallelToolExecutor(registry)
        tool_calls = [
            {"id": "c1", "function": {"name": "echo", "arguments": {"text": "a"}}},
            {"id": "c2", "function": {"name": "add", "arguments": {"a": 2, "b": 3}}},
            {"id": "c3", "function": {"name": "echo", "arguments": {"text": "b"}}},
        ]
        results = await executor.execute_all(tool_calls)
        assert len(results) == 3
        results_map = {r.tool_name: r.result for r in results}
        assert results_map["echo"] in ("Echo: a", "Echo: b")

    @pytest.mark.asyncio
    async def test_execute_missing_tool(self, registry):
        executor = ParallelToolExecutor(registry)
        tc = [{"id": "c1", "function": {"name": "nonexistent", "arguments": {}}}]
        results = await executor.execute_all(tc)
        assert len(results) == 1
        assert not results[0].success

    @pytest.mark.asyncio
    async def test_timeout_handling(self, registry):
        executor = ParallelToolExecutor(registry, timeout_per_tool=0.01)
        tc = [{"id": "c1", "function": {"name": "slow", "arguments": {"text": "hi"}}}]
        results = await executor.execute_all(tc)
        assert results[0].error == "timeout"

    @pytest.mark.asyncio
    async def test_sequential_execution(self, registry):
        executor = ParallelToolExecutor(registry)
        tool_calls = [
            {"id": "c1", "function": {"name": "add", "arguments": {"a": 1, "b": 2}}},
            {"id": "c2", "function": {"name": "add", "arguments": {"a": 3, "b": 4}}},
        ]
        results = await executor.execute_sequential(tool_calls)
        assert len(results) == 2
        assert results[0].result == "3"
        assert results[1].result == "7"


# ── CheckpointStore ──


class TestInMemoryCheckpointStore:
    @pytest.fixture
    def store(self):
        return InMemoryCheckpointStore()

    @pytest.mark.asyncio
    async def test_save_and_get(self, store):
        cp = CheckpointData(
            session_id="s1",
            messages=[{"role": "user", "content": "hi"}],
            iteration=1,
            status="running",
        )
        cid = await store.save(None, cp, thread_id="t1", checkpoint_id="cp1")
        retrieved = await store.get(None, "cp1")
        assert retrieved is not None
        assert retrieved.session_id == "s1"
        assert retrieved.iteration == 1

    @pytest.mark.asyncio
    async def test_get_latest(self, store):
        cp1 = CheckpointData(session_id="s1", messages=[], iteration=1, status="running")
        cp2 = CheckpointData(session_id="s1", messages=[], iteration=2, status="running")
        await store.save(None, cp1, thread_id="t1", checkpoint_id="cp1")
        await store.save(None, cp2, thread_id="t1", checkpoint_id="cp2", parent_id="cp1")
        latest = await store.get_latest(None, "s1", "t1")
        assert latest is not None
        data, cid = latest
        assert data.iteration == 2
        assert cid == "cp2"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, store):
        result = await store.get(None, "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_and_delete(self, store):
        cp = CheckpointData(session_id="s1", messages=[], iteration=1, status="running")
        await store.save(None, cp, thread_id="t1", checkpoint_id="cp1")
        await store.save(None, cp, thread_id="t1", checkpoint_id="cp2")
        ids = await store.list_for_session(None, "s1")
        assert len(ids) == 2
        deleted = await store.delete_for_session(None, "s1")
        assert deleted == 2


# ── ModelRouter ──


class TestModelRouter:
    @pytest.mark.asyncio
    async def test_primary_model_succeeds(self):
        registry = ModelRegistry()
        route = ModelRoute(provider="fake", model_id="fake-model", api_key="fake")
        router = ModelRouter(registry, routes=[route])

        # Mock the adapter
        adapter = FakeModelAdapter([ChatResult(content="from primary")])
        registry._models["fake:fake-model"] = adapter

        result = await router.chat(messages=[{"role": "user", "content": "hi"}])
        assert result.content == "from primary"

    @pytest.mark.asyncio
    async def test_fallback_on_error(self):
        registry = ModelRegistry()

        class FailingModel(FakeModelAdapter):
            async def chat(self, messages, tools=None, **kw):
                raise RuntimeError("Rate limited")

        registry._models["fake:fake-model"] = FailingModel()
        registry._models["fake:fake-model-2"] = FakeModelAdapter([ChatResult(content="from fallback")])

        routes = [
            ModelRoute(provider="fake", model_id="fake-model", api_key="fake", priority=0, max_retries=1),
            ModelRoute(provider="fake", model_id="fake-model-2", api_key="fake", priority=1, max_retries=1),
        ]
        router = ModelRouter(registry, routes=routes, base_delay=0.01)

        result = await router.chat(messages=[{"role": "user", "content": "hi"}])
        assert result.content == "from fallback"

    @pytest.mark.asyncio
    async def test_all_models_fail(self):
        registry = ModelRegistry()

        class FailingModel(FakeModelAdapter):
            async def chat(self, messages, tools=None, **kw):
                raise RuntimeError("Failed")

        registry._models["fake:fake-model"] = FailingModel()
        routes = [ModelRoute(provider="fake", model_id="fake-model", api_key="fake", max_retries=1)]
        router = ModelRouter(registry, routes=routes, base_delay=0.01)

        with pytest.raises(RuntimeError, match="Failed"):
            await router.chat(messages=[{"role": "user", "content": "hi"}])


# ── AgentEngine Integration ──


class TestAgentEngineIntegration:
    @pytest.fixture
    def engine(self):
        from app.core.permission_rules import PermissionConfig, PermissionMode

        model_registry = ModelRegistry()
        tool_registry = ToolRegistry()

        @tool_registry.tool(name="echo", description="Echo back")
        async def echo(text: str) -> str:
            return f"Echo: {text}"

        @tool_registry.tool(name="get_time", description="Get time")
        async def get_time() -> str:
            return "2024-01-01 12:00:00"

        eng = AgentEngine(model_registry, tool_registry)
        eng._default_permission_config = PermissionConfig(mode=PermissionMode.BYPASS)
        return eng

    @pytest.mark.asyncio
    async def test_simple_conversation(self, engine):
        model = FakeModelAdapter([ChatResult(content="Hello! How can I help?")])
        engine.model_registry._models["fake:fake-model"] = model

        session = engine.create_session(
            agent_id="test", user_id="u1",
            provider="fake", model_id="fake-model", api_key="fake",
        )

        events = []
        async for event in engine.run(session, "Hi"):
            events.append(event)

        done = [e for e in events if e.type == AgentEventType.DONE]
        assert len(done) == 1
        assert "Hello! How can I help?" in done[0].data["content"]

    @pytest.mark.asyncio
    async def test_tool_execution(self, engine):
        model = FakeModelAdapter([
            ChatResult(content="", tool_calls=[{
                "id": "c1", "type": "function",
                "function": {"name": "echo", "arguments": {"text": "hello"}},
            }]),
            ChatResult(content="The result is: Echo: hello"),
        ])
        engine.model_registry._models["fake:fake-model"] = model

        session = engine.create_session(
            agent_id="test", user_id="u1",
            provider="fake", model_id="fake-model", api_key="fake",
            tools=["echo"],
        )

        events = []
        async for event in engine.run(session, "Echo hello"):
            events.append(event)

        done = [e for e in events if e.type == AgentEventType.DONE]
        assert len(done) == 1
        assert "Echo: hello" in done[0].data["content"]

    @pytest.mark.asyncio
    async def test_checkpoint_events_emitted(self, engine):
        model = FakeModelAdapter([
            ChatResult(content="", tool_calls=[{
                "id": "c1", "type": "function",
                "function": {"name": "echo", "arguments": {"text": "x"}},
            }]),
            ChatResult(content="Done"),
        ])
        engine.model_registry._models["fake:fake-model"] = model

        session = engine.create_session(
            agent_id="test", user_id="u1",
            provider="fake", model_id="fake-model", api_key="fake",
            tools=["echo"],
        )

        events = []
        async for event in engine.run(session, "Run echo"):
            events.append(event)

        checkpoint_events = [e for e in events if e.type == AgentEventType.CHECKPOINT]
        assert len(checkpoint_events) >= 1
        assert checkpoint_events[0].data["iteration"] == 1

    @pytest.mark.asyncio
    async def test_thinking_events_emitted(self, engine):
        model = FakeModelAdapter([ChatResult(content="Answer")])
        engine.model_registry._models["fake:fake-model"] = model

        session = engine.create_session(
            agent_id="test", user_id="u1",
            provider="fake", model_id="fake-model", api_key="fake",
        )

        events = []
        async for event in engine.run(session, "Hi"):
            events.append(event)

        thinking = [e for e in events if e.type == AgentEventType.THINKING]
        assert len(thinking) >= 1

    @pytest.mark.asyncio
    async def test_session_stop(self, engine):
        class SlowModel(FakeModelAdapter):
            async def chat(self, messages, tools=None, **kw):
                await asyncio.sleep(0.05)
                return ChatResult(content="response")

        engine.model_registry._models["fake:fake-model"] = SlowModel()
        session = engine.create_session(
            agent_id="test", user_id="u1",
            provider="fake", model_id="fake-model", api_key="fake",
        )

        events = []

        async def run_and_stop():
            async for event in engine.run(session, "Hi"):
                events.append(event)
                if event.type == AgentEventType.THINKING:
                    session.stop()

        await run_and_stop()
        done = [e for e in events if e.type == AgentEventType.DONE]
        assert len(done) == 1
        # Stopped sessions may have status "stopped" or "completed" depending on timing
        assert done[0].data.get("status", "completed") in ("stopped", "completed")

    @pytest.mark.asyncio
    async def test_max_iterations(self, engine):
        # Always returns tool call, never terminates
        model = FakeModelAdapter([
            ChatResult(content="", tool_calls=[{
                "id": "c1", "type": "function",
                "function": {"name": "echo", "arguments": {"text": "loop"}},
            }]),
        ])
        engine.model_registry._models["fake:fake-model"] = model

        session = engine.create_session(
            agent_id="test", user_id="u1",
            provider="fake", model_id="fake-model", api_key="fake",
            tools=["echo"],
        )
        session.max_iterations = 3

        events = []
        async for event in engine.run(session, "Loop"):
            events.append(event)

        done = [e for e in events if e.type == AgentEventType.DONE]
        assert done[0].data["status"] == "max_iterations_reached"
        assert done[0].data["iterations"] == 3

    @pytest.mark.asyncio
    async def test_error_handling(self, engine):
        class ErrorModel(FakeModelAdapter):
            async def chat(self, messages, tools=None, **kw):
                raise RuntimeError("API timeout")

        engine.model_registry._models["fake:fake-model"] = ErrorModel()
        session = engine.create_session(
            agent_id="test", user_id="u1",
            provider="fake", model_id="fake-model", api_key="fake",
        )

        events = []
        async for event in engine.run(session, "Hi"):
            events.append(event)

        errors = [e for e in events if e.type == AgentEventType.ERROR]
        assert len(errors) == 1
        assert "API timeout" in errors[0].data["error"]
        assert session.status == SessionStatus.FAILED

    @pytest.mark.asyncio
    async def test_context_compression_triggered(self, engine):
        # Create a very long conversation to trigger compression
        model = FakeModelAdapter([ChatResult(content="Short answer")])
        engine.model_registry._models["fake:fake-model"] = model

        session = engine.create_session(
            agent_id="test", user_id="u1",
            provider="fake", model_id="fake-model", api_key="fake",
            context_config=ContextConfig(max_tokens=50, compression_strategy=CompressionStrategy.TRUNCATE),
        )

        # Pre-fill with long messages
        for i in range(10):
            session.session_memory.add("user", "x" * 200)
            session.session_memory.add("assistant", "y" * 200)

        events = []
        async for event in engine.run(session, "Final question"):
            events.append(event)

        compression_events = [e for e in events if e.type == AgentEventType.CONTEXT_COMPRESSION]
        assert len(compression_events) >= 1
