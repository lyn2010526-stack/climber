"""Regression tests for the Agent Factory critical path repairs."""

from __future__ import annotations

import asyncio
import json

import pytest

from app.models.openai_adapter import OpenAIAdapter


class _FakeStreamResponse:
    def __init__(self, lines: list[bytes]) -> None:
        self._lines = lines

    async def aiter_bytes(self):
        for line in self._lines:
            yield line

    async def aclose(self) -> None:
        return None

    def raise_for_status(self) -> None:
        return None


def _sse(chunk: dict) -> bytes:
    return f"data: {json.dumps(chunk)}\n\n".encode()


def _patch_stream(monkeypatch: pytest.MonkeyPatch, lines: list[bytes]) -> None:
    response = _FakeStreamResponse(lines)

    class _Client:
        async def send(self, request, **kwargs):
            return response

    monkeypatch.setattr(OpenAIAdapter, "get_client", classmethod(lambda cls: _Client()))


async def test_openai_done_marker_emits_single_final_result(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_stream(monkeypatch, [
        _sse({"choices": [{"delta": {"content": "Hel"}}]}),
        _sse({"choices": [{"delta": {"content": "lo"}}]}),
        b"data: [DONE]\n\n",
    ])

    adapter = OpenAIAdapter(model_id="gpt-4o-mini", api_key="k")
    chunks = [c async for c in adapter.stream_chat([{"role": "user", "content": "hi"}])]

    deltas = [c.content for c in chunks if c.content]
    assert deltas == ["Hel", "lo"]
    final = chunks[-1]
    assert final.content == ""
    assert final.finish_reason == "stop"
    assert final.accumulated_content == "Hello"


async def test_openai_tool_call_deltas_accumulate_without_duplication(monkeypatch: pytest.MonkeyPatch) -> None:
    first = {
        "choices": [
            {
                "delta": {"tool_calls": [
                    {"index": 0, "id": "call_1",
                     "function": {"name": "web_search", "arguments": '{"q"'}}
                ]},
            }
        ]
    }
    second = {
        "choices": [
            {"delta": {"tool_calls": [
                {"index": 0, "function": {"arguments": ': "x"}'}}
            ]}, "finish_reason": "tool_calls"}
        ]
    }
    _patch_stream(monkeypatch, [_sse(first), _sse(second), b"data: [DONE]\n\n"])

    adapter = OpenAIAdapter(model_id="gpt-4o-mini", api_key="k")
    chunks = [c async for c in adapter.stream_chat([{"role": "user", "content": "search"}])]
    accumulated: list[dict] = []
    for c in chunks:
        OpenAIAdapter._accumulate_tool_call_deltas(accumulated, c.tool_calls)

    assert len(accumulated) == 1
    assert accumulated[0]["id"] == "call_1"
    assert accumulated[0]["function"]["name"] == "web_search"
    assert json.loads(accumulated[0]["function"]["arguments"]) == {"q": "x"}


async def test_openai_chat_aggregates_stream_once(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_stream(monkeypatch, [
        _sse({"choices": [{"delta": {"content": "part1"}}]}),
        _sse({"choices": [{"delta": {"content": "part2"}}]}),
        b"data: [DONE]\n\n",
    ])
    adapter = OpenAIAdapter(model_id="gpt-4o-mini", api_key="k")
    result = await adapter.chat([{"role": "user", "content": "hi"}])
    assert result.content == "part1part2"
    assert result.finish_reason == "stop"


def test_capabilities_uses_current_model_fields() -> None:
    caps = OpenAIAdapter(model_id="m", api_key="k").capabilities
    assert caps.streaming is True
    assert caps.tools is True
    assert caps.max_tokens == 128000


# --- Task manager -----------------------------------------------------------

async def test_task_submit_persists_objective_without_api_key() -> None:
    from app.core.task_worker import TaskManager
    from app.storage import async_session
    from app.storage.models_platform import AutoLoopTask

    manager = TaskManager(max_workers=1)

    async def _handler(payload, on_progress):
        return {"output": "ok"}

    manager.register("agent_run", _handler)
    task_id = await manager.submit(
        "agent_run",
        {"objective": "build it", "api_key": "super-secret", "provider": "openai"},
    )

    async with async_session() as session:
        record = await session.get(AutoLoopTask, task_id)
        assert record is not None
        assert "super-secret" not in record.objective
        payload = json.loads(record.objective)
        assert payload["objective"] == "build it"

    status = await manager.get_status(task_id)
    assert status is not None
    assert status["objective"] == "build it"


async def test_task_cancel_marks_record_cancelled() -> None:
    from app.core.task_worker import TaskManager, TaskStatus
    from app.storage import async_session
    from app.storage.models_platform import AutoLoopTask

    manager = TaskManager(max_workers=1)
    started = asyncio.Event()

    async def _handler(payload, on_progress):
        started.set()
        await asyncio.sleep(30)
        return {"output": "never"}

    manager.register("agent_run", _handler)
    task_id = await manager.submit("agent_run", {"objective": "sleep"})
    await asyncio.wait_for(started.wait(), timeout=5)

    assert await manager.cancel(task_id) is True

    async def _cancelled() -> bool:
        async with async_session() as session:
            record = await session.get(AutoLoopTask, task_id)
            return record is not None and record.status == TaskStatus.CANCELLED.value

    assert await asyncio.wait_for(_cancelled(), timeout=5) is True
    assert await manager.cancel(task_id) is False


# --- API contracts ----------------------------------------------------------

async def test_sessions_messages_expose_tool_call_fields(client) -> None:
    session_resp = await client.post("/api/v1/sessions/", json={"title": "tools"})
    assert session_resp.status_code == 200
    session_id = session_resp.json()["id"]

    from app.core import MessageRole
    from app.core.engine.persistence import persist_message

    await persist_message(
        session_id,
        MessageRole.ASSISTANT,
        content="",
        tool_calls=[{"id": "call_9", "type": "function", "function": {"name": "web_search", "arguments": "{}"}}],
    )
    await persist_message(
        session_id, MessageRole.TOOL, content="result", tool_name="web_search", tool_call_id="call_9"
    )

    resp = await client.get(f"/api/v1/sessions/{session_id}/messages")
    assert resp.status_code == 200
    body = resp.json()
    assert "messages" in body
    assistant = next(m for m in body["messages"] if m["role"] == "assistant")
    tool = next(m for m in body["messages"] if m["role"] == "tool")
    assert assistant["tool_calls"][0]["id"] == "call_9"
    assert tool["tool_call_id"] == "call_9"
    assert tool["tool_name"] == "web_search"


async def test_tasks_submit_and_get_roundtrip(client) -> None:
    resp = await client.post(
        "/api/v1/tasks/submit",
        json={"task_type": "data_processing", "payload": {"data": ["a"], "operation": "uppercase"}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) >= {"task_id", "objective", "status", "progress", "total_steps"}

    task_id = body["task_id"]
    final = None
    for _ in range(100):
        status = await client.get(f"/api/v1/tasks/{task_id}")
        final = status.json()
        if final["status"] in {"completed", "failed", "cancelled"}:
            break
        await asyncio.sleep(0.05)

    assert final is not None
    assert final["status"] == "completed"
    assert final["result"]["results"] == ["A"]


async def test_factory_run_streams_agent_output(client, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_handler(payload, on_progress):
        await on_progress(1, 2, "thinking")
        await on_progress(2, 2, "done")
        return {"output": f"finished: {payload['objective']}"}

    from app.core.task_worker import task_manager

    monkeypatch.setitem(task_manager._handlers, "agent_run", _fake_handler)

    resp = await client.post(
        "/api/v1/skills/autonomous/run",
        json={"goal": "ship it", "skills": ["web_search"], "prompt_template": "senior-engineer"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = []
    for frame in resp.text.split("\n\n"):
        for line in frame.splitlines():
            if line.startswith("data: ") and line != "data: [DONE]":
                events.append(json.loads(line[6:]))

    types = [e["type"] for e in events]
    assert "plan" in types
    assert "task_start" in types
    assert "synthesize" in types
    assert next(e for e in events if e["type"] == "synthesize")["data"]["report"] == "finished: ship it"


async def test_factory_run_rejects_empty_goal(client) -> None:
    resp = await client.post("/api/v1/skills/autonomous/run", json={"goal": "   "})
    assert resp.status_code == 422


async def test_agent_run_handler_consumes_engine_events(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import AgentEvent, AgentEventType
    from app.core import agent_engine as agent_engine_module
    from app.core.di import resolve as real_resolve
    import app.core.di as di_module
    from app.core.task_worker import handle_agent_run

    class _Metrics:
        total_tokens_used = 7
        total_iterations = 2

    class _Session:
        max_iterations = 0
        metrics = _Metrics()

    class _FakeEngine:
        def __init__(self, *a, **k):
            pass

        def create_session(self, **kwargs):
            self.kwargs = kwargs
            return _Session()

        async def run(self, session, message):
            yield AgentEvent(type=AgentEventType.THINKING, data={"iteration": 1})
            yield AgentEvent(type=AgentEventType.TEXT, data={"content": "answer"})
            yield AgentEvent(type=AgentEventType.DONE, data={})

    monkeypatch.setattr(agent_engine_module, "AgentEngine", _FakeEngine)

    def _resolve_fallback(name):
        raise KeyError(name)

    monkeypatch.setattr(di_module, "resolve", _resolve_fallback)

    calls = []

    async def _on_progress(step, total, message=""):
        calls.append((step, total, message))

    result = await handle_agent_run({"objective": "go"}, _on_progress)
    assert result["output"] == "answer"
    assert result["tokens_used"] == 7
    assert calls[0][0] == 1
    assert calls[-1][2] == "Complete"


def test_crew_module_has_uuid_import() -> None:
    import app.multi_agent.crew as crew_module

    assert hasattr(crew_module, "uuid")
