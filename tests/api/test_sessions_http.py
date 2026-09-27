"""HTTP-level tests for ``/api/v1/sessions/*``.

The create/list/delete lifecycle is exercised through the real app, and the
delete case asserts the in-memory release the endpoint is responsible for: the
engine keeps its own session registry, so a delete that only removed the database
row would leave the session, its messages and its API key resident for the whole
process lifetime.
"""

from __future__ import annotations

import pytest

from tests.api.conftest import bearer


async def _create_session_row(session_id: str, user_id: str, title: str = "row") -> None:
    from app.storage import async_session
    from app.storage.database import Session as SessionModel

    async with async_session() as db:
        db.add(SessionModel(id=session_id, user_id=user_id, title=title, status="idle"))
        await db.commit()


# --- create / list / read ----------------------------------------------------


async def test_create_returns_an_id_and_persists_the_row(http) -> None:
    resp = await http.post("/api/v1/sessions/", json={"title": "http created"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"]
    assert body["session_id"] == body["id"]
    assert body["title"] == "http created"
    assert body["status"] == "idle"

    detail = await http.get(f"/api/v1/sessions/{body['id']}")
    assert detail.status_code == 200
    assert detail.json()["title"] == "http created"


async def test_create_defaults_the_title(http) -> None:
    resp = await http.post("/api/v1/sessions/", json={})

    assert resp.status_code == 200
    assert resp.json()["title"] == "New Session"


async def test_create_rejects_an_agent_owned_by_another_user(http, auth_on) -> None:
    from app.storage import async_session
    from app.storage.database import Agent

    async with async_session() as db:
        db.add(
            Agent(
                id="foreign-session-agent",
                user_id="owner-user",
                name="foreign",
                provider="openai",
                model_id="gpt-4o-mini",
            )
        )
        await db.commit()

    resp = await http.post(
        "/api/v1/sessions/",
        json={"agent_id": "foreign-session-agent"},
        headers=bearer("intruder-user"),
    )

    assert resp.status_code == 422
    assert resp.json()["detail"] == "Agent not found"


async def test_create_without_slash_is_a_separate_registered_route(http) -> None:
    """``redirect_slashes`` is off, so both spellings are distinct endpoints."""
    resp = await http.post("/api/v1/sessions", json={"title": "no slash"})

    assert resp.status_code == 200
    assert resp.json()["title"] == "no slash"


async def test_list_includes_a_created_session(http) -> None:
    created = (await http.post("/api/v1/sessions/", json={"title": "listed"})).json()

    resp = await http.get("/api/v1/sessions/")

    assert resp.status_code == 200
    items = resp.json()
    assert created["id"] in [item["id"] for item in items]
    entry = next(item for item in items if item["id"] == created["id"])
    assert set(entry) >= {"id", "title", "status", "created_at", "updated_at", "provider"}


async def test_list_does_not_leak_another_users_sessions(http, auth_on) -> None:
    owner = bearer("owner-user")
    created = (
        await http.post("/api/v1/sessions/", json={"title": "mine"}, headers=owner)
    ).json()

    resp = await http.get("/api/v1/sessions/", headers=bearer("somebody-else"))

    assert resp.status_code == 200
    assert created["id"] not in [item["id"] for item in resp.json()]


async def test_model_settings_are_reduced_to_known_keys(http) -> None:
    """``_clean_model_settings`` must drop a submitted api_key before persisting."""
    from sqlalchemy import select

    from app.storage import async_session
    from app.storage.database import Session as SessionModel

    resp = await http.post(
        "/api/v1/sessions/",
        json={
            "title": "with model",
            "model_settings": {
                "provider": "anthropic",
                "model_id": "claude-sonnet-4",
                "base_url": "https://example.invalid",
                "api_key": "sk-must-not-be-stored",
            },
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "anthropic"
    assert body["model_id"] == "claude-sonnet-4"

    async with async_session() as db:
        row = (
            await db.execute(select(SessionModel).where(SessionModel.id == body["id"]))
        ).scalar_one()
    assert "api_key" not in (row.model_settings or {})
    assert "sk-must-not-be-stored" not in repr(row.model_settings)


# --- read / messages / clear -------------------------------------------------


async def test_read_404s_for_an_unknown_session(http) -> None:
    resp = await http.get("/api/v1/sessions/does-not-exist")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Session not found"


async def test_read_is_404_across_users(http, auth_on) -> None:
    await _create_session_row("owned-sess", "owner-user")

    resp = await http.get("/api/v1/sessions/owned-sess", headers=bearer("intruder-user"))

    assert resp.status_code == 404


async def test_messages_are_empty_for_a_fresh_session(http) -> None:
    created = (await http.post("/api/v1/sessions/", json={"title": "empty msgs"})).json()

    resp = await http.get(f"/api/v1/sessions/{created['id']}/messages")

    assert resp.status_code == 200
    assert resp.json() == {"messages": []}


async def test_messages_are_404_across_users(http, auth_on) -> None:
    await _create_session_row("owned-msgs", "owner-user")

    resp = await http.get("/api/v1/sessions/owned-msgs/messages", headers=bearer("intruder-user"))

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Session not found"


async def test_clear_removes_persisted_messages(http) -> None:
    from app.core.engine.persistence import persist_message

    created = (await http.post("/api/v1/sessions/", json={"title": "clearable"})).json()
    await persist_message(created["id"], "user", content="hello")
    await persist_message(created["id"], "assistant", content="hi")

    before = await http.get(f"/api/v1/sessions/{created['id']}/messages")
    assert len(before.json()["messages"]) == 2

    resp = await http.post(f"/api/v1/sessions/{created['id']}/clear")

    assert resp.status_code == 200
    assert resp.json() == {"status": "cleared"}
    after = await http.get(f"/api/v1/sessions/{created['id']}/messages")
    assert after.json()["messages"] == []


async def test_clear_404s_across_users(http, auth_on) -> None:
    await _create_session_row("owned-clear", "owner-user")

    resp = await http.post("/api/v1/sessions/owned-clear/clear", headers=bearer("intruder-user"))

    assert resp.status_code == 404


# --- delete releases engine memory -------------------------------------------


async def test_delete_releases_the_in_memory_session(http, workflow_runtime) -> None:
    from app.api.v1.chat import get_engine

    created = (await http.post("/api/v1/sessions/", json={"title": "to delete"})).json()
    sid = created["id"]

    engine = get_engine()
    session = engine.create_session(
        agent_id="a",
        user_id="default-user",
        provider="openai",
        model_id="gpt-4o-mini",
        api_key="sk-should-be-released",
        session_id=sid,
    )
    assert sid in engine._sessions
    assert session.session_config.api_key == "sk-should-be-released"

    resp = await http.delete(f"/api/v1/sessions/{sid}")

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    # The engine keeps its own registry, so a row disappearing from SQL is not
    # enough: the live session object has to go as well.
    assert sid not in engine._sessions
    assert sid not in getattr(engine, "_session_order", set())
    # And the credential the released object was holding must not survive.
    assert session.session_config.api_key == ""


async def test_delete_of_an_unknown_session_is_404(http) -> None:
    resp = await http.delete("/api/v1/sessions/never-existed")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Session not found"


async def test_delete_is_404_across_users(http, auth_on, workflow_runtime) -> None:
    from app.api.v1.chat import get_engine

    await _create_session_row("owned-del", "owner-user")
    engine = get_engine()
    engine.create_session(
        agent_id="a",
        user_id="owner-user",
        provider="openai",
        model_id="m",
        api_key="k",
        session_id="owned-del",
    )

    resp = await http.delete("/api/v1/sessions/owned-del", headers=bearer("intruder-user"))

    assert resp.status_code == 404
    # A refused delete must leave the engine entry alone.
    assert "owned-del" in engine._sessions
    engine.close_session("owned-del")


async def test_delete_requires_authentication_when_auth_enabled(http, auth_on) -> None:
    await _create_session_row("guarded-del", "default-user")

    resp = await http.delete("/api/v1/sessions/guarded-del")

    assert resp.status_code == 401
    assert resp.json()["type"] == "authentication_required"


# --- checkpoint chain --------------------------------------------------------


async def test_resume_404s_when_there_is_no_checkpoint(http) -> None:
    created = (await http.post("/api/v1/sessions/", json={"title": "no ckpt"})).json()

    resp = await http.post(f"/api/v1/sessions/{created['id']}/resume")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "No checkpoint found to resume from"


async def test_latest_checkpoint_404s_when_the_chain_is_empty(http) -> None:
    created = (await http.post("/api/v1/sessions/", json={"title": "no latest"})).json()

    resp = await http.get(f"/api/v1/sessions/{created['id']}/checkpoint")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "No checkpoints found"


async def test_checkpoint_writes_truncate_at_the_retained_window(http) -> None:
    created = (await http.post("/api/v1/sessions/", json={"title": "ckpt window"})).json()
    sid = created["id"]

    for i in range(55):
        resp = await http.post(
            f"/api/v1/sessions/{sid}/checkpoint",
            json={"messages": [], "iteration": i, "status": "active"},
        )
        assert resp.status_code == 200
    assert resp.json()["total"] == 50

    history = await http.get(f"/api/v1/sessions/{sid}/history")
    assert resp.status_code == 200
    kept = history.json()["checkpoints"]
    assert len(kept) == 50
    # The five oldest entries are the ones dropped, so iteration 5 survives.
    assert kept[0]["iteration"] == 5
    assert kept[-1]["iteration"] == 54

    latest = await http.get(f"/api/v1/sessions/{sid}/checkpoint")
    assert latest.status_code == 200
    assert latest.json()["iteration"] == 54


async def test_rollback_discards_the_newer_checkpoints(http) -> None:
    created = (await http.post("/api/v1/sessions/", json={"title": "rb"})).json()
    sid = created["id"]

    ids = []
    for i in range(3):
        resp = await http.post(
            f"/api/v1/sessions/{sid}/checkpoint", json={"messages": [], "iteration": i}
        )
        ids.append(resp.json()["checkpoint_id"])

    resp = await http.post(f"/api/v1/sessions/{sid}/rollback", json={"checkpoint_id": ids[1]})

    assert resp.status_code == 200
    body = resp.json()
    assert body["discarded_checkpoints"] == 1
    assert body["total"] == 2
    assert body["checkpoint"]["iteration"] == 1

    history = await http.get(f"/api/v1/sessions/{sid}/history")
    assert [cp["iteration"] for cp in history.json()["checkpoints"]] == [0, 1]


async def test_rollback_to_an_unknown_checkpoint_is_404(http) -> None:
    created = (await http.post("/api/v1/sessions/", json={"title": "rb"})).json()

    resp = await http.post(
        f"/api/v1/sessions/{created['id']}/rollback", json={"checkpoint_id": "nope"}
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Checkpoint not found"


async def test_resume_replays_the_latest_checkpoint_snapshot(http) -> None:
    created = (await http.post("/api/v1/sessions/", json={"title": "resumable"})).json()
    sid = created["id"]
    snapshot = [{"role": "user", "content": "remember this"}]
    await http.post(
        f"/api/v1/sessions/{sid}/checkpoint",
        json={"messages": snapshot, "iteration": 7, "status": "active"},
    )

    resp = await http.post(f"/api/v1/sessions/{sid}/resume")

    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == sid
    assert body["status"] == "idle"
    assert body["checkpoint"]["iteration"] == 7
    assert body["checkpoint"]["messages"] == snapshot


async def test_checkpoint_write_is_404_across_users(http, auth_on) -> None:
    await _create_session_row("owned-ckpt", "owner-user")

    resp = await http.post(
        "/api/v1/sessions/owned-ckpt/checkpoint",
        json={"messages": [], "iteration": 1},
        headers=bearer("intruder-user"),
    )

    assert resp.status_code == 404


@pytest.mark.parametrize(
    ("path", "verb"),
    [
        ("/checkpoint", "GET"),
        ("/history", "GET"),
        ("/fork", "POST"),
        ("/rollback", "POST"),
        ("/resume", "POST"),
    ],
)
async def test_session_subresources_404_across_users(http, auth_on, path, verb) -> None:
    sid = f"owned{path.replace('/', '-')}"
    await _create_session_row(sid, "owner-user")
    body = {"checkpoint_id": "x"} if path == "/rollback" else {}

    resp = await http.request(
        verb, f"/api/v1/sessions/{sid}{path}", headers=bearer("intruder-user"), json=body
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Session not found"


# --- fork --------------------------------------------------------------------


async def test_fork_rejects_a_duplicate_target_id(http) -> None:
    src = (await http.post("/api/v1/sessions/", json={"title": "fork src"})).json()
    taken = (await http.post("/api/v1/sessions/", json={"title": "fork dst"})).json()

    resp = await http.post(
        f"/api/v1/sessions/{src['id']}/fork", json={"new_session_id": taken["id"]}
    )

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Target session id already exists"


async def test_fork_copies_messages_into_the_new_session(http) -> None:
    from app.core.engine.persistence import persist_message

    src = (await http.post("/api/v1/sessions/", json={"title": "fork with msgs"})).json()
    await persist_message(src["id"], "user", content="original")

    resp = await http.post(f"/api/v1/sessions/{src['id']}/fork", json={})

    assert resp.status_code == 200
    forked = resp.json()["session_id"]
    assert forked != src["id"]
    copied = await http.get(f"/api/v1/sessions/{forked}/messages")
    assert [m["content"] for m in copied.json()["messages"]] == ["original"]


async def test_fork_does_not_alias_the_source_history(http) -> None:
    """Clearing the fork must leave the source untouched."""
    from app.core.engine.persistence import persist_message

    src = (await http.post("/api/v1/sessions/", json={"title": "fork isolate"})).json()
    await persist_message(src["id"], "user", content="keep me")
    forked = (await http.post(f"/api/v1/sessions/{src['id']}/fork", json={})).json()["session_id"]

    await http.post(f"/api/v1/sessions/{forked}/clear")

    source_msgs = await http.get(f"/api/v1/sessions/{src['id']}/messages")
    fork_msgs = await http.get(f"/api/v1/sessions/{forked}/messages")
    assert [m["content"] for m in source_msgs.json()["messages"]] == ["keep me"]
    assert fork_msgs.json()["messages"] == []
