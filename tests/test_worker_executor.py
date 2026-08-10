"""Tests for the WorkerExecutor with mocked model registry and tool bridge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

import app.core.di as di
from app.core.stream_events import CollabEventType
from app.core.worker_executor import WorkerExecutor, _MemberInfo


@dataclass
class _Chunk:
    content: str = ""
    tool_calls: list[dict] | None = None
    tokens_used: int = 0


class _FakeAdapter:
    def __init__(self, chunks: list[_Chunk] | None = None, error: Exception | None = None):
        self._chunks = chunks or []
        self._error = error

    async def stream_chat(self, messages: list[dict], tools: list[dict] | None = None):
        if self._error is not None:
            raise self._error
        for chunk in self._chunks:
            yield chunk


class _FakeRegistry:
    def __init__(self, adapter: _FakeAdapter):
        self._adapter = adapter
        self.created: list[tuple[str, str]] = []

    def get_or_create(self, provider: str, model_id: str, api_key: str) -> _FakeAdapter:
        self.created.append((provider, model_id))
        return self._adapter


class _FakeBridge:
    def __init__(self, tool_result: str = "tool-output"):
        self._tool_result = tool_result
        self.executed: list[tuple[str, dict]] = []

    def list_tools(self, tool_names: list[str] | None = None, is_worker: bool = True) -> list[dict]:
        return [{"name": "run_command", "description": "run"}] if is_worker else []

    async def execute(self, tool_name: str, arguments: dict) -> Any:
        self.executed.append((tool_name, arguments))
        return type("TR", (), {"output": self._tool_result})


def _member(**kw: Any) -> _MemberInfo:
    defaults = {
        "id": "m1",
        "name": "worker-1",
        "provider": "fake",
        "model_id": "model-1",
        "api_key": "key",
        "tools": ["run_command"],
    }
    defaults.update(kw)
    return _MemberInfo(**defaults)


def _make_executor(
    registry: _FakeRegistry | None = None,
    bridge: _FakeBridge | None = None,
) -> WorkerExecutor:
    if registry is None:
        registry = _FakeRegistry(_FakeAdapter([_Chunk(content="hello")]))
    if bridge is None:
        bridge = _FakeBridge()
    di.register("ModelRegistry", registry)
    return WorkerExecutor("session-1", tool_bridge=bridge)


@pytest.fixture(autouse=True)
def _clean_di():
    yield
    di.clear()


async def _collect(executor: WorkerExecutor) -> list:
    return [event async for event in executor.execute(_member(), "do thing", "good", [])]


@pytest.mark.asyncio
async def test_worker_emits_start_and_done():
    executor = _make_executor()
    events = await _collect(executor)

    types = [e.type for e in events]
    assert types[0] == CollabEventType.WORKER_START
    assert types[-1] == CollabEventType.WORKER_DONE
    done = events[-1]
    assert done.data["content"] == "hello"
    assert done.data["tokens_used"] == 0


@pytest.mark.asyncio
async def test_worker_model_init_failure_emits_error():
    class _BadRegistry:
        def get_or_create(self, *args, **kwargs):
            raise RuntimeError("no model")

    di.register("ModelRegistry", _BadRegistry())
    executor = WorkerExecutor("session-1", tool_bridge=_FakeBridge())
    events = await _collect(executor)

    assert events[0].type == CollabEventType.WORKER_START
    assert events[1].type == CollabEventType.ERROR
    assert "no model" in events[1].data["error"]


@pytest.mark.asyncio
async def test_worker_stream_error_emits_error_event():
    adapter = _FakeAdapter(error=RuntimeError("stream blew up"))
    registry = _FakeRegistry(adapter)
    executor = _make_executor(registry=registry)
    events = await _collect(executor)

    assert events[-1].type == CollabEventType.ERROR
    assert "stream blew up" in events[-1].data["error"]


@pytest.mark.asyncio
async def test_worker_executes_tool_and_emits_call_and_result():
    bridge = _FakeBridge(tool_result="result-42")
    tool_chunk = _Chunk(tool_calls=[{"id": "tc-1", "function": {"name": "run_command", "arguments": "{\"command\": \"ls\"}"}}])
    adapter = _FakeAdapter([tool_chunk, _Chunk(content="final")])
    executor = _make_executor(registry=_FakeRegistry(adapter), bridge=bridge)

    events = await _collect(executor)

    types = [e.type for e in events]
    assert CollabEventType.WORKER_TOOL_CALL in types
    assert CollabEventType.WORKER_TOOL_RESULT in types
    assert bridge.executed == [("run_command", {"command": "ls"})]

    done = events[-1]
    assert done.type == CollabEventType.WORKER_DONE
    assert done.data["content"] == "final"


@pytest.mark.asyncio
async def test_worker_registers_member_with_registry():
    executor = _make_executor()
    await _collect(executor)

    registry = di.resolve("ModelRegistry")
    assert registry.created == [("fake", "model-1")]


@pytest.mark.asyncio
async def test_format_history_handles_empty_and_last_ten():
    executor = _make_executor()
    assert executor._format_history([]) == "No previous discussion."

    history = [{"role": "user", "content": f"msg-{i}"} for i in range(12)]
    formatted = executor._format_history(history)
    lines = [line for line in formatted.splitlines() if line.startswith("[user]")]
    assert len(lines) == 10
    assert "[user] msg-2" in lines
    assert "[user] msg-11" in lines
    assert not any(line == "[user] msg-0" for line in lines)
