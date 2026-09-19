"""Contract tests for per-session model overrides."""

from __future__ import annotations


async def test_create_session_persists_and_lists_model_override(client) -> None:
    created = await client.post(
        "/api/v1/sessions/",
        json={
            "title": "override",
            "model_settings": {"provider": "deepseek", "model_id": "deepseek-chat", "junk": "drop"},
        },
    )
    assert created.status_code == 200
    body = created.json()
    session_id = body["id"]
    assert body["provider"] == "deepseek"
    assert body["model_id"] == "deepseek-chat"

    listed = await client.get("/api/v1/sessions/")
    assert listed.status_code == 200
    row = next(item for item in listed.json() if item["id"] == session_id)
    assert row["provider"] == "deepseek"
    assert row["model_id"] == "deepseek-chat"

    detail = await client.get(f"/api/v1/sessions/{session_id}")
    assert detail.status_code == 200
    assert detail.json()["provider"] == "deepseek"
    assert detail.json()["model_id"] == "deepseek-chat"

    from app.storage import async_session
    from app.storage.database import Session as SessionModel

    async with async_session() as db:
        record = await db.get(SessionModel, session_id)
    assert "junk" not in record.model_settings


async def test_session_without_override_lists_null_model(client) -> None:
    created = await client.post("/api/v1/sessions/", json={"title": "plain"})
    assert created.status_code == 200
    assert created.json()["provider"] is None
    assert created.json()["model_id"] is None

    listed = await client.get("/api/v1/sessions/")
    row = next(item for item in listed.json() if item["id"] == created.json()["id"])
    assert row["model_id"] is None


async def test_legacy_create_endpoint_persists_override(client) -> None:
    created = await client.post(
        "/api/v1/sessions/create",
        json={"title": "legacy", "model_settings": {"model_id": "glm-4"}},
    )
    assert created.status_code == 200
    from app.storage import async_session
    from app.storage.database import Session as SessionModel

    async with async_session() as db:
        record = await db.get(SessionModel, created.json()["id"])
    assert record.model_settings == {"model_id": "glm-4"}


class _FakeRun:
    def __init__(self, session, message):
        pass

    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration


class _FakeEngine:
    def __init__(self):
        self._sessions: dict = {}
        self.created: dict = {}

    def create_session(self, **kwargs):
        self.created = kwargs

        class _Session:
            def __init__(self, user_id):
                self.user_id = user_id

        return _Session(kwargs.get("user_id", ""))

    def run(self, session, message):
        return _FakeRun(session, message)


async def test_chat_applies_session_model_override(client, monkeypatch) -> None:
    from app.api.v1 import chat as chat_module

    created = await client.post(
        "/api/v1/sessions/",
        json={
            "title": "chat-override",
            "model_settings": {"provider": "deepseek", "model_id": "deepseek-chat"},
        },
    )
    assert created.status_code == 200
    session_id = created.json()["id"]

    fake = _FakeEngine()
    monkeypatch.setattr(chat_module, "get_engine", lambda: fake)
    monkeypatch.setattr(chat_module.RecoveryManager, "restore_session", lambda self, session: _noop())

    stream = await client.post(f"/api/v1/sessions/{session_id}/chat", json={"message": "hi"})
    assert stream.status_code == 200
    await stream.aread()

    assert fake.created["provider"] == "deepseek"
    assert fake.created["model_id"] == "deepseek-chat"


async def _noop():
    return None


async def _seed_agent(agent_id: str) -> None:
    from app.storage import async_session
    from app.storage.database import Agent as AgentModel

    async with async_session() as db:
        db.add(AgentModel(
            id=agent_id,
            name="chat-model-test",
            provider="openai",
            model_id="gpt-4o-mini",
            api_key_encrypted="",
            user_id="default-user",
        ))
        await db.commit()


async def _drop_agent(agent_id: str) -> None:
    from app.storage import async_session
    from app.storage.database import Agent as AgentModel

    async with async_session() as db:
        row = await db.get(AgentModel, agent_id)
        if row is not None:
            await db.delete(row)
            await db.commit()


async def _chat_kwargs_for(session_id: str, monkeypatch) -> dict:
    """Exercise the chat model-resolution path without the HTTP app wiring."""
    from app.api.v1 import chat as chat_module
    from app.main import app as fastapi_app

    fake = _FakeEngine()
    monkeypatch.setattr(chat_module, "get_engine", lambda: fake)
    monkeypatch.setattr(chat_module.RecoveryManager, "restore_session", lambda self, session: _noop())

    dependency_overrides = dict(fastapi_app.dependency_overrides)
    fastapi_app.dependency_overrides[chat_module.get_current_user] = lambda: "default-user"
    try:
        stream = await chat_module.chat(
            session_id, chat_module.ChatRequest(message="hi"), user_id="default-user"
        )
        async for _ in stream.body_iterator:
            pass
    finally:
        fastapi_app.dependency_overrides.clear()
        fastapi_app.dependency_overrides.update(dependency_overrides)
    return fake.created


async def test_chat_same_provider_override_keeps_agent_key(client, monkeypatch) -> None:
    agent_id = "chat-model-test-agent"
    await _seed_agent(agent_id)
    try:
        created = await client.post(
            "/api/v1/sessions/",
            json={"title": "same-provider", "agent_id": agent_id, "model_settings": {"model_id": "gpt-4o"}},
        )
        assert created.status_code == 200
        assert created.json()["provider"] == "openai"
        assert created.json()["model_id"] == "gpt-4o"

        kwargs = await _chat_kwargs_for(created.json()["id"], monkeypatch)
        assert kwargs["provider"] == "openai"
        assert kwargs["model_id"] == "gpt-4o"
        assert kwargs["agent_id"] == agent_id
    finally:
        await _drop_agent(agent_id)
