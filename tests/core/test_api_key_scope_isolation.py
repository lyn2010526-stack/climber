"""API key ownership and scope-escalation regressions."""

from __future__ import annotations

import pytest

from app.config import settings
from app.core.auth_manager import hash_password
from app.storage import async_session


@pytest.fixture
def enable_auth():
    settings.enable_auth = True
    yield
    settings.enable_auth = False


async def _create_user(username: str, password: str, role: str) -> int:
    from app.models.users import User, UserStatus

    async with async_session() as session:
        user = User(
            username=username,
            email=f"{username}@test.local",
            hashed_password=hash_password(password),
            role=role,
            status=UserStatus.ACTIVE.value,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return int(user.id)


async def _login(client, username: str, password: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_create_key_ignores_client_owner_and_uses_caller(client, enable_auth) -> None:
    alice_id = await _create_user("alice_owner", "secret123", "user")
    bob_token = await _login(client, "alice_owner", "secret123")

    response = await client.post(
        "/api/v1/auth/keys",
        headers=_auth(bob_token),
        json={"name": "attempt", "owner": "999999"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["owner"] == str(alice_id)


async def test_create_key_rejects_admin_scope_for_non_admin(client, enable_auth) -> None:
    await _create_user("carol", "secret123", "user")
    token = await _login(client, "carol", "secret123")

    response = await client.post(
        "/api/v1/auth/keys",
        headers=_auth(token),
        json={"name": "privesc", "scopes": ["read", "admin"]},
    )
    assert response.status_code == 403


async def test_admin_can_create_key_with_admin_scope(client, enable_auth) -> None:
    admin_id = await _create_user("keys_admin", "secret123", "admin")
    token = await _login(client, "keys_admin", "secret123")

    response = await client.post(
        "/api/v1/auth/keys",
        headers=_auth(token),
        json={"name": "ops", "scopes": ["read", "admin"]},
    )
    assert response.status_code == 200
    assert set(response.json()["scopes"]) == {"read", "admin"}
    assert response.json()["owner"] == str(admin_id)


async def test_list_keys_filtered_by_owner(client, enable_auth) -> None:
    await _create_user("list_alice", "secret123", "user")
    await _create_user("list_bob", "secret123", "user")
    alice = await _login(client, "list_alice", "secret123")
    bob = await _login(client, "list_bob", "secret123")

    created = await client.post("/api/v1/auth/keys", headers=_auth(alice), json={"name": "a1"})
    assert created.status_code == 200
    alice_key_id = created.json()["id"]

    await client.post("/api/v1/auth/keys", headers=_auth(bob), json={"name": "b1"})

    listed = await client.get("/api/v1/auth/keys", headers=_auth(bob))
    assert listed.status_code == 200
    ids = {key["id"] for key in listed.json()["keys"]}
    assert alice_key_id not in ids
    assert len(ids) == 1


async def test_revoke_only_own_key(client, enable_auth) -> None:
    await _create_user("rev_alice", "secret123", "user")
    await _create_user("rev_bob", "secret123", "user")
    alice = await _login(client, "rev_alice", "secret123")
    bob = await _login(client, "rev_bob", "secret123")

    created = await client.post("/api/v1/auth/keys", headers=_auth(alice), json={"name": "a"})
    key_id = created.json()["id"]

    forbidden = await client.delete(f"/api/v1/auth/keys/{key_id}", headers=_auth(bob))
    assert forbidden.status_code == 403

    allowed = await client.delete(f"/api/v1/auth/keys/{key_id}", headers=_auth(alice))
    assert allowed.status_code == 200


async def test_ttl_bounds_enforced(client, enable_auth) -> None:
    await _create_user("ttl_user", "secret123", "user")
    token = await _login(client, "ttl_user", "secret123")

    response = await client.post(
        "/api/v1/auth/keys",
        headers=_auth(token),
        json={"name": "long", "ttl_days": 5000},
    )
    assert response.status_code == 422


async def test_created_key_authenticates_and_carries_scopes(client, enable_auth) -> None:
    await _create_user("usable", "secret123", "user")
    token = await _login(client, "usable", "secret123")
    created = await client.post(
        "/api/v1/auth/keys",
        headers=_auth(token),
        json={"name": "usable", "scopes": ["read"]},
    )
    raw_key = created.json()["raw_key"]
    from app.core.auth_manager import validate_api_key

    info = await validate_api_key(raw_key)
    assert info["user_id"] == created.json()["owner"]
    assert info["scopes"] == ["read"]
