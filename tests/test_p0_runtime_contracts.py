"""Regression tests for the primary workspace API contracts."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.chat import ChatRequest, chat
from app.api.v1.doctor import _run_diagnostics
from app.api.v1.sessions import SessionPage
from app.core.agent_engine import AgentSession
from app.storage import async_session
from app.storage.database import Agent

DEFAULT_USER_ID = "default-user"


async def _get_current_user(credentials) -> dict:
    if credentials.credentials == "invalid":
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"id": credentials.credentials}


def test_session_page_accepts_paginated_response() -> None:
    page = SessionPage.model_validate(
        {
            "items": [
                {
                    "id": "session-1",
                    "title": "First session",
                    "status": "idle",
                    "created_at": "2026-07-29T00:00:00",
                    "updated_at": "2026-07-29T00:00:00",
                }
            ],
            "total": 1,
            "limit": 50,
            "offset": 0,
        }
    )

    assert page.total == 1
    assert page.items[0].id == "session-1"


@pytest.mark.skip(reason="Auth removed for local-only mode")
def test_auth_endpoint_token_is_verifiable() -> None:
    from app.api.v1.auth import _issue_access_token

    token = _issue_access_token("user-1")

    assert token.access_token == "user-1"






@pytest.mark.asyncio
@pytest.mark.skip(reason="Auth removed for local-only mode")
async def test_auth_me_allows_guest_without_credentials(client) -> None:
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["id"] == DEFAULT_USER_ID




@pytest.mark.skip(reason="Auth removed for local-only mode")
@pytest.mark.asyncio
async def test_authenticated_identity_and_agent_ownership(client) -> None:
    owner_response = await client.post(
        "/api/v1/auth/register",
        json={"email": "owner-p0@test.local", "password": "pass12345"},
    )
    requester_response = await client.post(
        "/api/v1/auth/register",
        json={"email": "requester-p0@test.local", "password": "pass12345"},
    )
    owner_headers = {"Authorization": f"Bearer {owner_response.json()['access_token']}"}
    requester_headers = {"Authorization": f"Bearer {requester_response.json()['access_token']}"}

    owner_identity = await client.get("/api/v1/auth/me", headers=owner_headers)
    assert owner_identity.status_code == 200
    assert owner_identity.json()["email"] == "owner-p0@test.local"

    async with async_session() as session:
        agent = Agent(
            user_id=owner_identity.json()["id"],
            name="Owner agent",
            provider="openai",
            model_id="gpt-4o-mini",
        )
        session.add(agent)
        await session.commit()
        await session.refresh(agent)

    session_response = await client.post(
        "/api/v1/sessions",
        headers=requester_headers,
        json={"agent_id": agent.id},
    )

    assert session_response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.skip(reason="Auth removed for local-only mode")
async def test_chat_rejects_in_memory_session_owned_by_another_user() -> None:
    session = AgentSession(
        session_id="session-1",
        agent_id="agent-1",
        user_id="owner-1",
        provider="openai",
        model_id="gpt-4o-mini",
        api_key="placeholder",
    )
    engine = type("Engine", (), {"_sessions": {session.session_id: session}})()

    with patch("app.api.v1.chat.get_engine", return_value=engine):
        with pytest.raises(HTTPException) as exc_info:
            await chat(session.session_id, ChatRequest(message="hello"), user_id="other-user")

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_doctor_awaits_database_health_check() -> None:
    health = AsyncMock(
        return_value={
            "connected": True,
            "backend": "sqlite",
            "journal_mode": "wal",
        }
    )
    redis = AsyncMock(return_value=None)

    with (
        patch("app.storage.db_health", health),
        patch("app.storage.cache.get_redis", redis),
    ):
        report = await _run_diagnostics()

    health.assert_awaited_once()
    redis.assert_awaited_once()
    database = next(section for section in report["sections"] if section["section"] == "database")
    assert database["checks"][0] == {
        "name": "connected",
        "ok": True,
        "detail": "sqlite",
    }
