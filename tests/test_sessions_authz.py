"""Regression tests for the P1-1 IDOR and P1-2 JWT-assurance audit items.

P1-1: the session endpoints used ``if not row or (row.user_id and row.user_id !=
user_id)``, which passes when ``row.user_id`` is NULL, so a NULL-owner row was
readable and mutable by any caller and ``clear_session`` deleted every message
in it. P1-2: the JWT branch of the auth middleware trusted the token's ``sub``
without touching the database, unlike the API key branch.

Every test builds real rows in a real database. The NULL-owner test rebuilds
``sessions`` with a nullable ``user_id`` column, because both the Alembic
migrations and ``Base.metadata.create_all`` declare it NOT NULL, so a NULL row
cannot be produced without recreating the schema variant the audit describes.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import sessions as sessions_api
from app.config import settings
from app.core.auth_manager import create_access_token
from app.middleware.auth import authenticate_credentials
import app.storage as storage
from app.storage.database import Message as MessageModel
from app.storage.database import Session as SessionModel

OWNER = "user-a"
INTRUDER = "user-b"
NULL_OWNER_SESSION = "session-null-owner"

# A sessions table whose user_id column allows NULL, matching the schema the
# audit describes for the create_all bootstrap path and historical rows.
_NULLABLE_USER_ID_SCHEMA = """
CREATE TABLE sessions (
    id VARCHAR(36) NOT NULL,
    agent_id VARCHAR(36),
    user_id VARCHAR(36),
    status VARCHAR(20) NOT NULL,
    title VARCHAR(255),
    model_settings JSON NOT NULL,
    context_data JSON NOT NULL,
    iteration_count INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    working_memory JSON NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (id)
)
"""


# --- fixtures ---------------------------------------------------------------


@pytest.fixture
async def null_owner_engine(tmp_path, monkeypatch):
    """Point the sessions router at a database that can hold a NULL owner.

    Yields an engine whose ``sessions`` table has a nullable ``user_id`` and
    whose ``messages`` table matches the real one. Sessions are restored on
    teardown, so the shared test database is untouched.
    """
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'null_owner.db'}",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.execute(text(_NULLABLE_USER_ID_SCHEMA))
        await conn.execute(
            text("""
            CREATE TABLE messages (
                id VARCHAR(36) NOT NULL,
                session_id VARCHAR(36) NOT NULL,
                role VARCHAR(20) NOT NULL,
                content TEXT,
                tool_call_id VARCHAR(100),
                tool_calls JSON NOT NULL,
                tool_name VARCHAR(100),
                tokens INTEGER NOT NULL,
                metadata JSON NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                parent_id VARCHAR(36),
                branch_id VARCHAR(36) NOT NULL,
                children_count INTEGER NOT NULL,
                PRIMARY KEY (id),
                FOREIGN KEY(session_id) REFERENCES sessions (id)
            )
            """)
        )
        await conn.execute(
            text(
                "INSERT INTO sessions (id, user_id, status, title, model_settings, context_data,"
                " iteration_count, total_tokens, working_memory)"
                " VALUES (:id, NULL, 'idle', 'legacy orphan', '{}', '{}', 0, 0, '{}')"
            ),
            {"id": NULL_OWNER_SESSION},
        )
        for suffix in ("1", "2"):
            await conn.execute(
                text(
                    "INSERT INTO messages (id, session_id, role, content, tool_calls, tokens,"
                    " metadata, branch_id, children_count)"
                    " VALUES (:id, :session_id, 'user', :content, '[]', 0, '{}', 'main', 0)"
                ),
                {
                    "id": f"msg-{suffix}",
                    "session_id": NULL_OWNER_SESSION,
                    "content": f"secret-{suffix}",
                },
            )

    monkeypatch.setattr(sessions_api, "async_session", async_sessionmaker(engine))
    try:
        yield engine
    finally:
        await engine.dispose()


async def _seed_owned_session(session_id: str, user_id: str, message_count: int = 2) -> None:
    """Insert a session owned by ``user_id`` plus real messages, as other tests do."""
    async with storage.async_session() as db:
        db.add(
            SessionModel(
                id=session_id,
                user_id=user_id,
                status="idle",
                title=f"owned by {user_id}",
            )
        )
        for index in range(message_count):
            db.add(
                MessageModel(
                    id=f"{session_id}-msg-{index}",
                    session_id=session_id,
                    role="user",
                    content=f"message {index}",
                )
            )
        await db.commit()


async def _message_ids(session_id: str) -> list[str]:
    async with storage.async_session() as db:
        result = await db.execute(
            text("SELECT id FROM messages WHERE session_id = :sid ORDER BY id"), {"sid": session_id}
        )
        return [row[0] for row in result.fetchall()]


async def _session_exists(session_id: str) -> bool:
    async with storage.async_session() as db:
        return await db.get(SessionModel, session_id) is not None


def _read_endpoints() -> list[Any]:
    """Every sessions.py handler that reads a single session by id."""
    return [
        sessions_api.get_session,
        sessions_api.get_session_messages,
        sessions_api.get_latest_checkpoint,
        sessions_api.get_checkpoint_history,
        sessions_api.resume_session,
    ]


# --- P1-1: a NULL user_id row is invisible to every caller -------------------


@pytest.mark.parametrize("endpoint", _read_endpoints(), ids=lambda fn: fn.__name__)
async def test_null_owner_session_is_not_readable_by_any_user(null_owner_engine, endpoint) -> None:
    """The regression the audit is about: a NULL owner must never grant access."""
    with pytest.raises(HTTPException) as exc_info:
        await endpoint(NULL_OWNER_SESSION, user_id=INTRUDER)
    assert exc_info.value.status_code == 404

    # A NULL owner is not "owned by the local identity" either.
    with pytest.raises(HTTPException) as exc_info:
        await endpoint(NULL_OWNER_SESSION, user_id="default-user")
    assert exc_info.value.status_code == 404


async def test_null_owner_session_is_not_mutable_by_any_user(null_owner_engine) -> None:
    """A NULL owner must block every write path, not just the read paths."""
    with pytest.raises(HTTPException) as exc_info:
        await sessions_api.delete_session(NULL_OWNER_SESSION, user_id=INTRUDER)
    assert exc_info.value.status_code == 404

    async with null_owner_engine.begin() as conn:
        survivor = (
            await conn.execute(
                text("SELECT COUNT(*) FROM sessions WHERE id = :sid"), {"sid": NULL_OWNER_SESSION}
            )
        ).scalar_one()
    assert survivor == 1, "delete_session removed a row it did not own"


@pytest.mark.parametrize("endpoint", _read_endpoints(), ids=lambda fn: fn.__name__)
async def test_null_owner_session_is_not_loaded_as_an_owned_row(null_owner_engine, endpoint) -> None:
    """The shared _load_owned_session helper must not hand back a NULL-owner row."""
    async with async_sessionmaker(null_owner_engine)() as db:
        with pytest.raises(HTTPException) as exc_info:
            await sessions_api._load_owned_session(db, NULL_OWNER_SESSION, INTRUDER)
        assert exc_info.value.status_code == 404

        with pytest.raises(HTTPException) as exc_info:
            await sessions_api._ensure_owned_session(NULL_OWNER_SESSION, INTRUDER)
        assert exc_info.value.status_code == 404


# --- P1-1: cross-user isolation on a row that does have an owner -------------


async def test_owned_session_is_rejected_for_another_user_and_allowed_for_its_owner() -> None:
    session_id = "session-owned-by-a"
    await _seed_owned_session(session_id, OWNER)

    with pytest.raises(HTTPException) as exc_info:
        await sessions_api.get_session(session_id, user_id=INTRUDER)
    assert exc_info.value.status_code == 404

    own = await sessions_api.get_session(session_id, user_id=OWNER)
    assert own["id"] == session_id

    messages = await sessions_api.get_session_messages(session_id, user_id=OWNER)
    assert [m.content for m in messages["messages"]] == ["message 0", "message 1"]

    with pytest.raises(HTTPException) as exc_info:
        await sessions_api.delete_session(session_id, user_id=INTRUDER)
    assert exc_info.value.status_code == 404
    assert await _session_exists(session_id) is True

    await sessions_api.delete_session(session_id, user_id=OWNER)
    assert await _session_exists(session_id) is False


# --- P1-1: clear_session must not wipe another user's messages ---------------


async def test_clear_session_cannot_delete_another_users_messages() -> None:
    session_id = "session-clear-victim"
    await _seed_owned_session(session_id, OWNER, message_count=3)
    assert len(await _message_ids(session_id)) == 3

    with pytest.raises(HTTPException) as exc_info:
        await sessions_api.clear_session(session_id, user_id=INTRUDER)
    assert exc_info.value.status_code == 404
    assert await _message_ids(session_id) == [
        f"{session_id}-msg-0",
        f"{session_id}-msg-1",
        f"{session_id}-msg-2",
    ]

    cleared = await sessions_api.clear_session(session_id, user_id=OWNER)
    assert cleared == {"status": "cleared"}
    assert await _message_ids(session_id) == []


async def test_clear_session_cannot_delete_a_null_owner_sessions_messages(
    null_owner_engine,
) -> None:
    """The worst case named by the audit: a cross-user DELETE of all messages."""
    with pytest.raises(HTTPException) as exc_info:
        await sessions_api.clear_session(NULL_OWNER_SESSION, user_id=INTRUDER)
    assert exc_info.value.status_code == 404

    async with null_owner_engine.begin() as conn:
        remaining = (
            await conn.execute(
                text("SELECT COUNT(*) FROM messages WHERE session_id = :sid"),
                {"sid": NULL_OWNER_SESSION},
            )
        ).scalar_one()
    assert remaining == 2, "clear_session deleted messages it did not own"


# --- P1-2: the JWT branch verifies the principal against the database --------


@pytest.fixture
def enable_auth():
    settings.enable_auth = True
    try:
        yield
    finally:
        settings.enable_auth = False


async def _create_user(username: str, status: str, role: str = "viewer") -> int:
    from sqlalchemy import select as sa_select

    from app.core.auth_manager import hash_password
    from app.models.users import User

    async with storage.async_session() as db:
        db.add(
            User(
                username=username,
                email=f"{username}@test.local",
                hashed_password=hash_password(secrets.token_urlsafe(16)),
                role=role,
                status=status,
            )
        )
        await db.commit()
        result = await db.execute(sa_select(User.id).where(User.username == username))
        return result.scalar_one()


async def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _assert_not_authenticated(result: Any) -> None:
    """A refused credential must be indistinguishable from a missing one."""
    assert result is None


async def test_jwt_rejects_unknown_subject(enable_auth) -> None:
    """A correctly signed token for a subject with no user row must be refused."""
    token = create_access_token("999999", ["admin"])

    _assert_not_authenticated(await authenticate_credentials(await _bearer(token)))


async def test_jwt_rejects_deactivated_user(enable_auth) -> None:
    """An active-then-deactivated user must lose access immediately."""
    user_id = await _create_user("suspended_user", "suspended")
    token = create_access_token(str(user_id), ["read", "write"])

    _assert_not_authenticated(await authenticate_credentials(await _bearer(token)))


async def test_jwt_rejects_deactivated_user_over_http(client, enable_auth) -> None:
    """The middleware turns a refused subject into a 401, never a 200."""
    user_id = await _create_user("suspended_http_user", "suspended")
    token = create_access_token(str(user_id), ["read", "write"])

    response = await client.get("/api/v1/sessions/", headers=await _bearer(token))
    assert response.status_code == 401


async def test_jwt_accepts_active_user_and_carries_role(enable_auth) -> None:
    """The happy path still works and now carries a database-backed role."""
    user_id = await _create_user("active_user", "active", role="admin")
    token = create_access_token(str(user_id), ["read", "write"])

    result = await authenticate_credentials(await _bearer(token))
    assert result is not None
    assert result["method"] == "jwt"
    assert result["sub"] == str(user_id)
    assert result["user_id"] == str(user_id)
    assert result["username"] == "active_user"
    assert result["role"] == "admin"


async def test_jwt_rejects_token_without_sub(enable_auth) -> None:
    """A signature-valid token carrying no subject must fail closed."""
    import base64
    import hmac
    import json

    from app.core.auth_manager import _secret

    payload = {
        "type": "access",
        "scopes": ["admin"],
        "iat": datetime.now(UTC).isoformat(),
        "exp": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    signature = hmac.new(_secret().encode(), encoded.encode(), "sha256").hexdigest()[:16]

    _assert_not_authenticated(
        await authenticate_credentials(await _bearer(f"{encoded}.{signature}"))
    )


async def test_jwt_rejects_expired_token(enable_auth) -> None:
    """Expiry is still enforced before the database lookup runs."""
    import base64
    import hmac
    import json

    from app.core.auth_manager import _secret

    user_id = await _create_user("expiring_user", "active")
    payload = {
        "sub": str(user_id),
        "type": "access",
        "scopes": ["read"],
        "iat": (datetime.now(UTC) - timedelta(hours=2)).isoformat(),
        "exp": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    signature = hmac.new(_secret().encode(), encoded.encode(), "sha256").hexdigest()[:16]

    with pytest.raises(HTTPException) as exc_info:
        await authenticate_credentials(await _bearer(f"{encoded}.{signature}"))
    assert exc_info.value.status_code == 401


async def test_jwt_rejects_refresh_token_used_as_access(enable_auth) -> None:
    """A refresh token must not authenticate the middleware as an access token."""
    from app.core.auth_manager import create_refresh_token

    user_id = await _create_user("refresh_only_user", "active")
    refresh = create_refresh_token(str(user_id), ["read"])

    with pytest.raises(HTTPException) as exc_info:
        await authenticate_credentials(await _bearer(refresh))
    assert exc_info.value.status_code == 401


async def test_jwt_rejects_tampered_signature(enable_auth) -> None:
    """A token whose signature no longer matches must be refused."""
    user_id = await _create_user("tampered_user", "active")
    token = create_access_token(str(user_id), ["read", "write"])

    with pytest.raises(HTTPException) as exc_info:
        await authenticate_credentials(await _bearer(f"{token}.tampered"))
    assert exc_info.value.status_code == 401


async def test_jwt_rejects_malformed_token(enable_auth) -> None:
    """A credential that is not a token at all must be refused."""
    with pytest.raises(HTTPException) as exc_info:
        await authenticate_credentials(await _bearer("not-a-token"))
    assert exc_info.value.status_code == 401
