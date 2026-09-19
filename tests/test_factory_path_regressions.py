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

    from app.api.v1 import skills_router
    from app.core.task_worker import task_manager

    async def _factory_payload(user_id, data):
        return {
            "objective": data["goal"],
            "user_id": user_id,
            "provider": "openai",
            "model": "test-model",
            "api_key": "test-key",
            "base_url": None,
            "system_prompt": "test",
            "tools": ["web_search"],
            "factory_skills": data.get("skills", []),
            "max_steps": 10,
        }

    monkeypatch.setattr(skills_router, "_factory_agent_payload", _factory_payload)
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
    assert "factory_start" in types
    assert "plan" in types
    assert "task_start" in types
    assert "task_complete" in types
    assert "synthesize" in types
    report = next(e for e in events if e["type"] == "synthesize")["data"]["report"]
    assert "Produce the final answer" in report


async def test_factory_retries_failed_step(client, monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0

    async def _flaky_handler(payload, on_progress):
        nonlocal attempts
        attempts += 1
        if payload["objective"] == "recover this" and attempts == 2:
            raise RuntimeError("temporary model failure")
        return {"output": "recovered"}

    from app.api.v1 import skills_router
    from app.core.task_worker import task_manager

    async def _factory_payload(user_id, data):
        return {
            "objective": data["goal"],
            "user_id": user_id,
            "provider": "openai",
            "model": "test-model",
            "api_key": "test-key",
            "base_url": None,
            "system_prompt": "test",
            "tools": ["run_command"],
            "factory_skills": data.get("skills", []),
            "max_steps": 10,
        }

    monkeypatch.setattr(skills_router, "_factory_agent_payload", _factory_payload)
    monkeypatch.setitem(task_manager._handlers, "agent_run", _flaky_handler)
    resp = await client.post(
        "/api/v1/skills/autonomous/run",
        json={"goal": "recover this", "skills": ["code_executor"]},
    )
    assert resp.status_code == 200
    assert '"type": "task_retry"' in resp.text
    assert '"type": "synthesize"' in resp.text


async def test_factory_run_rejects_empty_goal(client) -> None:
    resp = await client.post("/api/v1/skills/autonomous/run", json={"goal": "   "})
    assert resp.status_code == 422


async def test_agent_run_handler_consumes_engine_events(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.core.di as di_module
    from app.core import AgentEvent, AgentEventType
    from app.core import agent_engine as agent_engine_module
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


def test_permission_config_roundtrips_through_dict() -> None:
    from app.core.permission_rules import (
        PermissionConfig,
        PermissionMode,
        PermissionRule,
        RuleDecision,
    )

    cfg = PermissionConfig(
        mode=PermissionMode.AUTO,
        rules=[PermissionRule(decision=RuleDecision.DENY, tool="run_command", pattern="rm *")],
        allowed_tools=["web_search"],
        denied_tools=["file_delete"],
    )
    restored = PermissionConfig.from_dict(cfg.to_dict())
    assert restored.mode == PermissionMode.AUTO
    assert restored.rules[0].decision == RuleDecision.DENY
    assert restored.rules[0].tool == "run_command"
    assert restored.rules[0].pattern == "rm *"
    assert restored.allowed_tools == ["web_search"]
    assert restored.denied_tools == ["file_delete"]


async def test_engine_persists_and_propagates_permission_config(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.agent_engine import AgentEngine
    from app.core.permission_rules import PermissionConfig, PermissionMode

    monkeypatch.setenv("CLIMBER_DATA_DIR", str(tmp_path))
    engine = AgentEngine()
    session = engine.create_session(
        agent_id="t", user_id="u", provider="openai", model_id="m", api_key="k",
    )
    new_config = PermissionConfig(mode=PermissionMode.AUTO)
    engine.update_permission_config(new_config)

    assert session.permission_config is new_config
    assert (tmp_path / "permission_config.json").exists()

    engine2 = AgentEngine()
    reloaded = engine2.get_permission_config()
    assert reloaded is not None
    assert reloaded.mode == PermissionMode.AUTO


async def test_budget_endpoint_returns_current_spend(client) -> None:
    from app.storage import async_session
    from app.storage.models_cost import BudgetConfig, CostRecord

    async with async_session() as db:
        db.add(BudgetConfig(user_id="default-user", amount=25.0, period="monthly", is_active=True))
        db.add(CostRecord(
            user_id="default-user", provider="openai", model_id="gpt-4o-mini",
            prompt_tokens=10, completion_tokens=5, total_tokens=15,
            input_cost=0.01, output_cost=0.02, total_cost=0.03,
        ))
        await db.commit()

    resp = await client.get("/api/v1/cost/budget")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) >= {"amount", "period", "is_active", "current_spend", "per_session_limit", "per_request_limit"}
    assert body["amount"] == 25.0
    assert body["is_active"] is True
    assert body["current_spend"] == round(0.03, 6)


async def test_auth_me_returns_user_object(client) -> None:
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, dict)
    assert {"id", "username", "email", "role"} <= set(body)
    assert body["id"] == body["username"]


async def test_settings_exposes_mcp_ready(client) -> None:
    resp = await client.get("/api/v1/settings/")
    assert resp.status_code == 200
    body = resp.json()
    assert "mcp_ready" in body
    assert "mcp_status" in body
    assert body["mcp_ready"] == (body["mcp_status"] == "ready")


# ── Sandbox escape regressions (#105/#106/#107) ───────────────────────────────


def test_safe_eval_rejects_dunder_attribute_escape() -> None:
    """safe_eval must block __class__/__subclasses__ traversal."""
    from app.workflow.engine import safe_eval

    with pytest.raises(ValueError, match="attribute"):
        safe_eval("[].__class__", {})
    with pytest.raises(ValueError):
        safe_eval("[].__class__.__bases__[0].__subclasses__()", {})
    with pytest.raises(ValueError):
        safe_eval("(1).__class__", {})


def test_safe_exec_rejects_dunder_attribute_escape() -> None:
    """safe_exec must block dunder attribute traversal too."""
    from app.workflow.engine import safe_exec

    with pytest.raises(ValueError, match="attribute"):
        safe_exec("x = [].__class__", {})


def test_safe_eval_allows_legitimate_expressions() -> None:
    """Non-dunder expressions still work after the fix."""
    from app.workflow.engine import safe_eval

    assert safe_eval("len([1, 2, 3])", {}) == 3
    assert safe_eval("x + 1", {"x": 41}) == 42
    assert safe_eval("[i * 2 for i in range(3)]", {}) == [0, 2, 4]


# ── Scheduler identity-check regression (#73/#74) ─────────────────────────────


async def test_scheduler_list_filters_by_user_and_schedule(client) -> None:
    """list_scheduled must filter by user_id AND non-null schedule."""
    # Non-scheduled workflow for default user — must NOT appear.
    resp = await client.post(
        "/api/v1/scheduler",
        json={"name": "Unscheduled", "nodes": [], "edges": []},
    )
    assert resp.status_code == 200
    # Scheduled workflow — must appear.
    resp2 = await client.post(
        "/api/v1/scheduler",
        json={"name": "Daily", "schedule": "0 9 * * *", "nodes": [], "edges": []},
    )
    assert resp2.status_code == 200
    listed = (await client.get("/api/v1/scheduler")).json()
    names = {w["name"] for w in listed}
    assert "Daily" in names
    assert "Unscheduled" not in names


# ── vector_memory hardening regressions (#58/#59/#60) ─────────────────────────


def test_vector_memory_collection_name_sanitized() -> None:
    """Path separators and control chars are stripped from collection names."""
    from app.core.vector_memory import _COLLECTION_NAME_RE

    cleaned = _COLLECTION_NAME_RE.sub("_", "user/../../etc/passwd")
    assert "/" not in cleaned
    assert "\\" not in cleaned
    assert "\x00" not in cleaned


async def test_vector_memory_run_works_in_async_context() -> None:
    """_run uses get_running_loop (no DeprecationWarning) in async callers."""
    from app.core.vector_memory import VectorMemoryService

    fut = VectorMemoryService._run(lambda: 42)
    assert await fut == 42


class _FakeChatResult:
    def __init__(self, content: str) -> None:
        self.content = content
        self.total_tokens = 50
        self.prompt_tokens = 20
        self.completion_tokens = 30
        self.input_tokens = 20
        self.output_tokens = 30


class _FakeModelAdapter:
    provider = "openai"
    model_id = "gpt-4o"
    api_key = "sk-test"
    total_tokens = 0

    class capabilities:
        chat = True
        streaming = True
        tools = False
        vision = False
        embedding = False
        max_tokens = 4096

    async def chat(self, messages, **kwargs):
        return _FakeChatResult(
            "Proposed solution: build a CLI tool with argparse and tests. "
            "Edge cases: empty input, unicode, huge files. Alternative: use click. "
            "Reasoning: CLI simplest with tests. Risk: parsing bugs mitigated by unit tests. "
            "Conclusion: build the CLI with argparse and test coverage."
        )

    async def stream_chat(self, messages, **kwargs):
        yield await self.chat(messages)


def test_model_registry_resolves_single_string_spec() -> None:
    from app.models.registry import ModelRegistry

    reg = ModelRegistry()
    adapter = reg.get_or_create("gpt-4o-mini")
    assert reg.get_model("openai", "gpt-4o-mini") is adapter
    default = reg.get_default()
    assert reg.get_model("openai", "gpt-4o") is default


async def test_reasoning_endpoint_returns_result(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /reason wires the ModelRegistry contract and finishes a full run."""
    from types import SimpleNamespace

    from app.core.reasoning.service import ReasoningService
    from app.models.registry import ModelRegistry

    reg = ModelRegistry()
    reg._models["openai:gpt-4o"] = _FakeModelAdapter()
    fake_engine = SimpleNamespace(
        reasoning=ReasoningService(model_registry=reg),
        model_registry=reg,
    )
    monkeypatch.setattr("app.api.v1.get_engine", lambda: fake_engine)

    resp = await client.post(
        "/api/v1/reason",
        json={
            "task": "Design a CLI tool in Python that renames files in bulk.",
            "mode": "auto",
            "coverage_enabled": False,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"]
    assert len(body["candidates"]) >= 1


# ── Track A auth hardening regressions ─────────────────────────────────────


async def test_require_admin_rejects_non_admin_principal(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi import HTTPException

    from app.config import settings
    from app.core.auth_manager import require_admin
    from app.core.principal import Principal, reset_current_principal, set_current_principal

    monkeypatch.setattr(settings, "enable_auth", True)
    dep = require_admin()

    token = set_current_principal(Principal(subject_id="u1", scopes=("read", "write")))
    try:
        with pytest.raises(HTTPException) as exc_info:
            await dep(request=None)
        assert exc_info.value.status_code == 403
    finally:
        reset_current_principal(token)

    token = set_current_principal(Principal(subject_id="u2", scopes=("read", "write", "admin")))
    try:
        result = await dep(request=None)
        assert result["user_id"] == "u2"
    finally:
        reset_current_principal(token)


async def test_require_scopes_admin_bypass_and_enforcement(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi import HTTPException

    from app.config import settings
    from app.core.auth_manager import require_scopes
    from app.core.principal import Principal, reset_current_principal, set_current_principal

    monkeypatch.setattr(settings, "enable_auth", True)
    dep = require_scopes("write")

    token = set_current_principal(Principal(subject_id="u3", scopes=("admin",)))
    try:
        result = await dep(request=None)
        assert result["user_id"] == "u3"
    finally:
        reset_current_principal(token)

    token = set_current_principal(Principal(subject_id="u4", scopes=("read",)))
    try:
        with pytest.raises(HTTPException) as exc_info:
            await dep(request=None)
        assert exc_info.value.status_code == 403
    finally:
        reset_current_principal(token)


def test_verify_token_rejects_expired_without_secret_leak() -> None:
    import base64
    import hmac
    import json
    from datetime import UTC, datetime, timedelta

    from fastapi import HTTPException

    from app.config import settings
    from app.core.auth_manager import verify_token

    payload = {
        "sub": "1",
        "scopes": ["read"],
        "iat": (datetime.now(UTC) - timedelta(hours=48)).isoformat(),
        "exp": (datetime.now(UTC) - timedelta(hours=24)).isoformat(),
    }
    pb = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    secret = settings.app_secret_key
    sig = hmac.new(secret.encode(), pb.encode(), "sha256").hexdigest()[:16]
    with pytest.raises(HTTPException) as exc_info:
        verify_token(f"{pb}.{sig}")
    assert exc_info.value.status_code == 401
    assert "expired" in str(exc_info.value.detail).lower()


async def test_workflow_export_blocks_cross_tenant_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Under auth, a non-admin caller cannot export another user's workflow."""
    from httpx import ASGITransport, AsyncClient

    from app.config import settings
    from app.core.auth_manager import create_access_token
    from app.main import app

    monkeypatch.setattr(settings, "enable_auth", True)
    owner_tok = create_access_token("owner-user", ["read", "write"])
    intruder_tok = create_access_token("intruder-user", ["read", "write"])
    admin_tok = create_access_token("admin-user", ["read", "write", "admin"])
    owner_h = {"Authorization": f"Bearer {owner_tok}"}
    intruder_h = {"Authorization": f"Bearer {intruder_tok}"}
    admin_h = {"Authorization": f"Bearer {admin_tok}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post("/api/v1/workflows/", json={"name": "Secret Flow"}, headers=owner_h)
        assert created.status_code == 200
        wf_id = created.json()["id"]
        owner_row = await ac.get("/api/v1/workflows/", headers=owner_h)
        assert any(w["id"] == wf_id for w in owner_row.json())
        intruder_row = await ac.get("/api/v1/workflows/", headers=intruder_h)
        assert all(w["id"] != wf_id for w in intruder_row.json())

        denied_post = await ac.post(f"/api/v1/workflows/{wf_id}/export", json={"format": "json"}, headers=intruder_h)
        denied_get = await ac.get(f"/api/v1/workflows/{wf_id}/export", headers=intruder_h)
        assert denied_post.status_code == 404
        assert denied_get.status_code == 404

        allowed = await ac.post(f"/api/v1/workflows/{wf_id}/export", json={"format": "json"}, headers=owner_h)
        assert allowed.status_code == 200
        admin_view = await ac.post(f"/api/v1/workflows/{wf_id}/export", json={"format": "json"}, headers=admin_h)
        assert admin_view.status_code == 200
