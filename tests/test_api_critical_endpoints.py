"""Regression tests for previously crashing API endpoints.

Covers:
- /sessions/{id}/checkpoint, /history, /fork, /resume (must return parseable JSON)
- /groups/{id}/messages field access (sender_id vs. real model field agent_id)
"""

from __future__ import annotations


async def test_session_checkpoint_flow_returns_structured_json(client) -> None:
    created = await client.post("/api/v1/sessions/", json={"title": "ckpt-flow"})
    assert created.status_code == 200
    sid = created.json()["id"]

    saved = await client.post(
        f"/api/v1/sessions/{sid}/checkpoint",
        json={"messages": [{"role": "user", "content": "hi"}], "iteration": 2, "status": "active"},
    )
    assert saved.status_code == 200
    body = saved.json()
    assert body["status"] == "saved"
    assert body["checkpoint_id"]
    assert body["session_id"] == sid

    latest = await client.get(f"/api/v1/sessions/{sid}/checkpoint")
    assert latest.status_code == 200
    ckpt = latest.json()
    assert ckpt["iteration"] == 2
    assert ckpt["messages"][0]["content"] == "hi"

    history = await client.get(f"/api/v1/sessions/{sid}/history")
    assert history.status_code == 200
    assert len(history.json()["checkpoints"]) == 1

    resume = await client.post(f"/api/v1/sessions/{sid}/resume")
    assert resume.status_code == 200
    resumed = resume.json()
    assert resumed["session_id"] == sid
    assert resumed["checkpoint"]["iteration"] == 2


async def test_session_fork_copies_session(client) -> None:
    created = await client.post("/api/v1/sessions/", json={"title": "fork-src"})
    sid = created.json()["id"]
    await client.post(
        f"/api/v1/sessions/{sid}/checkpoint",
        json={"messages": [], "iteration": 1},
    )

    forked = await client.post(f"/api/v1/sessions/{sid}/fork", json={})
    assert forked.status_code == 200
    new_id = forked.json()["session_id"]
    assert new_id != sid

    detail = await client.get(f"/api/v1/sessions/{new_id}")
    assert detail.status_code == 200
    assert "fork" in detail.json()["title"]

    duplicate = await client.post(
        f"/api/v1/sessions/{sid}/fork", json={"new_session_id": new_id}
    )
    assert duplicate.status_code == 409


async def test_session_resume_without_checkpoint_is_structured_404(client) -> None:
    created = await client.post("/api/v1/sessions/", json={"title": "no-ckpt"})
    sid = created.json()["id"]
    resume = await client.post(f"/api/v1/sessions/{sid}/resume")
    assert resume.status_code == 404
    assert "detail" in resume.json()


async def test_session_checkpoint_missing_session_is_404(client) -> None:
    missing = await client.get("/api/v1/sessions/nope/checkpoint")
    assert missing.status_code == 404


async def test_group_messages_use_real_agent_id_field(client) -> None:
    from app.storage import async_session
    from app.storage.models_groups import AgentGroup, AgentGroupMessage

    group_id = "crit-group-msg"
    async with async_session() as db:
        db.add(AgentGroup(id=group_id, name="msg-group", user_id="default-user"))
        db.add(
            AgentGroupMessage(
                group_id=group_id,
                agent_id="reviewer-1",
                sender_name="Reviewer",
                content="approved",
                message_type="text",
            )
        )
        await db.commit()

    resp = await client.get(f"/api/v1/groups/{group_id}/messages")
    assert resp.status_code == 200
    messages = resp.json()["messages"]
    assert len(messages) == 1
    assert messages[0]["sender_id"] == "reviewer-1"
    assert messages[0]["agent_id"] == "reviewer-1"
    assert messages[0]["sender_name"] == "Reviewer"


async def test_session_rollback_truncates_checkpoint_chain(client) -> None:
    created = await client.post("/api/v1/sessions/", json={"title": "rollback-src"})
    sid = created.json()["id"]

    ids = []
    for iteration in (1, 2, 3):
        saved = await client.post(
            f"/api/v1/sessions/{sid}/checkpoint",
            json={"messages": [{"role": "user", "content": f"turn {iteration}"}], "iteration": iteration},
        )
        assert saved.status_code == 200
        ids.append(saved.json()["checkpoint_id"])

    rolled = await client.post(
        f"/api/v1/sessions/{sid}/rollback", json={"checkpoint_id": ids[1]}
    )
    assert rolled.status_code == 200
    body = rolled.json()
    assert body["status"] == "rolled_back"
    assert body["checkpoint"]["iteration"] == 2
    assert body["discarded_checkpoints"] == 1
    assert body["total"] == 2

    # resume now reflects the rollback point, not iteration 3
    resumed = await client.post(f"/api/v1/sessions/{sid}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["checkpoint"]["iteration"] == 2

    history = await client.get(f"/api/v1/sessions/{sid}/history")
    assert len(history.json()["checkpoints"]) == 2


async def test_session_rollback_to_first_and_unknown(client) -> None:
    created = await client.post("/api/v1/sessions/", json={"title": "rollback-first"})
    sid = created.json()["id"]
    ids = []
    for iteration in (1, 2):
        saved = await client.post(
            f"/api/v1/sessions/{sid}/checkpoint",
            json={"messages": [], "iteration": iteration},
        )
        ids.append(saved.json()["checkpoint_id"])

    rolled = await client.post(f"/api/v1/sessions/{sid}/rollback", json={"checkpoint_id": ids[0]})
    assert rolled.status_code == 200
    assert rolled.json()["discarded_checkpoints"] == 1

    unknown = await client.post(
        f"/api/v1/sessions/{sid}/rollback", json={"checkpoint_id": "does-not-exist"}
    )
    assert unknown.status_code == 404


async def test_session_rollback_requires_checkpoint_body(client) -> None:
    created = await client.post("/api/v1/sessions/", json={"title": "rollback-body"})
    sid = created.json()["id"]
    missing = await client.post(f"/api/v1/sessions/{sid}/rollback", json={})
    assert missing.status_code == 422
