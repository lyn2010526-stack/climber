"""Principal isolation and strict API v1 contract tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import Request
from httpx import ASGITransport, AsyncClient

from app.core.principal import (
    Principal,
    get_current_principal,
    reset_current_principal,
    set_current_principal,
)
from app.main import app


async def _test_principal(request: Request) -> Principal:
    return Principal(
        subject_id=request.headers.get("X-Test-User", "user-a"),
        tenant_id=request.headers.get("X-Test-Tenant", "tenant-test"),
        role="member",
        scopes=("read", "write"),
        auth_method="test",
    )


@pytest_asyncio.fixture
async def principal_client() -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_current_principal] = _test_principal
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.pop(get_current_principal, None)


async def _create_agent(client: AsyncClient, user_id: str, **values: Any) -> dict[str, Any]:
    body = {"name": f"agent-{uuid4()}", **values}
    response = await client.post(
        "/api/v1/agents", json=body, headers={"X-Test-User": user_id}
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_two_users_cannot_read_each_others_agents(
    principal_client: AsyncClient,
) -> None:
    agent = await _create_agent(principal_client, "user-a")

    own = await principal_client.get(
        f"/api/v1/agents/{agent['id']}", headers={"X-Test-User": "user-a"}
    )
    other = await principal_client.get(
        f"/api/v1/agents/{agent['id']}", headers={"X-Test-User": "user-b"}
    )

    assert own.status_code == 200
    assert other.status_code == 404


@pytest.mark.asyncio
async def test_agent_contract_rejects_invalid_and_unknown_body_fields(
    principal_client: AsyncClient,
) -> None:
    invalid = await principal_client.post("/api/v1/agents", json={"provider": "openai"})
    unknown = await principal_client.post(
        "/api/v1/agents", json={"name": "strict", "unexpected": True}
    )

    assert invalid.status_code == 422
    assert isinstance(invalid.json()["detail"], list)
    assert unknown.status_code == 422
    assert any(error["type"] == "extra_forbidden" for error in unknown.json()["detail"])


@pytest.mark.asyncio
async def test_agent_data_envelope_and_secret_response_redaction(
    principal_client: AsyncClient,
) -> None:
    response = await principal_client.post(
        "/api/v1/agents",
        json={
            "data": {
                "name": "enveloped-agent",
                "api_key": "secret-value",
                "api_key_encrypted": "legacy-secret-value",
            }
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "enveloped-agent"
    assert "api_key" not in body
    assert "api_key_encrypted" not in body
    assert "env" not in body


@pytest.mark.asyncio
async def test_group_and_task_references_are_scoped_to_owner_and_parent(
    principal_client: AsyncClient,
) -> None:
    agent_a = await _create_agent(principal_client, "user-a")
    agent_b = await _create_agent(principal_client, "user-b")
    group_response = await principal_client.post(
        "/api/v1/groups", json={"name": "owned-group"}, headers={"X-Test-User": "user-a"}
    )
    assert group_response.status_code == 200
    group_id = group_response.json()["id"]

    foreign_member = await principal_client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"agent_id": agent_b["id"]},
        headers={"X-Test-User": "user-a"},
    )
    assert foreign_member.status_code == 422

    member_response = await principal_client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"agent_id": agent_a["id"]},
        headers={"X-Test-User": "user-a"},
    )
    assert member_response.status_code == 200, member_response.text
    member_id = member_response.json()["id"]

    task_response = await principal_client.post(
        "/api/v1/tasks",
        json={
            "group_id": group_id,
            "description": "scoped task",
            "worker_id": member_id,
            "reviewer_ids": ["foreign-member"],
        },
        headers={"X-Test-User": "user-a"},
    )
    assert task_response.status_code == 422


@pytest.mark.asyncio
async def test_workflow_run_rejects_foreign_agent(
    principal_client: AsyncClient,
) -> None:
    foreign_agent = await _create_agent(principal_client, "user-b")
    workflow_response = await principal_client.post(
        "/api/v1/workflows",
        json={"name": "owned-workflow", "nodes": [{"id": "start"}]},
        headers={"X-Test-User": "user-a"},
    )
    workflow_id = workflow_response.json()["id"]

    run_response = await principal_client.post(
        f"/api/v1/workflows/{workflow_id}/run",
        json={"agent_id": foreign_agent["id"]},
        headers={"X-Test-User": "user-a"},
    )
    assert run_response.status_code == 422


def test_openapi_has_named_bodies_hidden_slash_aliases_and_unique_operation_ids() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    migrated_writes = (
        ("/api/v1/agents", "post"),
        ("/api/v1/workflows", "post"),
        ("/api/v1/workflows/{workflow_id}", "put"),
        ("/api/v1/workflows/{workflow_id}/run", "post"),
        ("/api/v1/crews", "post"),
        ("/api/v1/crews/{crew_id}/run", "post"),
        ("/api/v1/groups", "post"),
        ("/api/v1/groups/{group_id}/members", "post"),
        ("/api/v1/tasks", "post"),
        ("/api/v1/skills", "post"),
    )
    for path, method in migrated_writes:
        body_schema = paths[path][method]["requestBody"]["content"]["application/json"]["schema"]
        assert "$ref" in body_schema or any("$ref" in item for item in body_schema.get("anyOf", []))

    for collection in ("agents", "workflows", "crews", "groups", "tasks", "skills"):
        assert f"/api/v1/{collection}/" not in paths

    operation_ids = [
        operation["operationId"]
        for path_item in paths.values()
        for operation in path_item.values()
        if isinstance(operation, dict) and "operationId" in operation
    ]
    assert len(operation_ids) == len(set(operation_ids))


@pytest.mark.asyncio
async def test_collaboration_runner_propagates_principal_user(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.collaboration import agent_runner

    captured: dict[str, Any] = {}

    class FakeEngine:
        def __init__(self, **kwargs: Any) -> None:
            del kwargs

        def create_session(self, **kwargs: Any) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace()

        async def run(self, session: Any, message: str) -> AsyncIterator[Any]:
            del session, message
            if False:
                yield None

    monkeypatch.setattr(agent_runner, "AgentEngine", FakeEngine)
    monkeypatch.setattr(agent_runner, "di_resolve", lambda name: name)
    principal = Principal(subject_id="propagated-user", auth_method="test")

    events = agent_runner.run_agent(
        "agent-id", "provider", "model", "key", "prompt", "message", [], principal=principal
    )
    async for _event in events:
        pass

    assert captured["user_id"] == "propagated-user"


@pytest.mark.asyncio
async def test_tool_and_memory_context_use_explicit_principal() -> None:
    from app.core.memory_tool_context import get_memory_tool_context
    from app.core.tool_gateway import ToolGateway

    class FakeRegistry:
        def get_tool(self, name: str) -> SimpleNamespace:
            del name
            return SimpleNamespace(parameters={})

        async def execute(self, name: str, arguments: dict[str, Any]) -> str:
            del name, arguments
            return get_memory_tool_context().user_id

    principal = Principal(subject_id="context-user", auth_method="test")
    token = set_current_principal(principal)
    try:
        result = await ToolGateway(FakeRegistry()).execute("memory", {})  # type: ignore[arg-type]
    finally:
        reset_current_principal(token)

    assert result.output == "context-user"


@pytest.mark.asyncio
async def test_rate_limiter_uses_principal_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.middleware import rate_limit

    captured: list[str] = []

    async def check_rate_limit(identity: str) -> tuple[bool, str]:
        captured.append(identity)
        return True, "ok"

    monkeypatch.setattr(rate_limit.usage_tracker, "check_rate_limit", check_rate_limit)
    principal = Principal(
        subject_id="rate-user",
        tenant_id="rate-tenant",
        auth_method="api_key",
    )

    await rate_limit.RateLimiter()(SimpleNamespace(), principal)  # type: ignore[arg-type]

    assert captured == ["api_key:rate-tenant:rate-user"]
