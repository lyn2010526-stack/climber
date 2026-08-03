"""Security fixes verification tests.

Validates that critical security vulnerabilities have been properly addressed:
1. Placeholder api_key raises proper error
2. Weak SHA-256 password hashing replaced by PBKDF2
3. API key ownership enforced
4. User enumeration protected (admin-only list_users, switch_user removed)
5. Settings uses authenticated user
"""

import os
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

os.environ["APP_TESTING"] = "true"

from app.main import app
from app.storage import init_db, engine, Base
try:
    from app.storage.auth import hash_password, verify_password
except ImportError:
    hash_password = None
    verify_password = None


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(init_db())
    finally:
        loop.close()
    yield


@pytest.fixture(autouse=True)
def cleanup_db():
    yield
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        async def _cleanup():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await init_db()
        loop.run_until_complete(_cleanup())
    finally:
        loop.close()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── 1. Placeholder api_key raises proper error ────────────────────────────


@pytest.mark.skip(reason="User model removed for local-only mode")
@pytest.mark.asyncio
async def test_placeholder_api_key_raises_error(client, monkeypatch):
    pass


# ── 2. Weak password hashing replaced by PBKDF2 ───────────────────────────


@pytest.mark.skip(reason="Auth removed for local-only mode")
def test_hash_password_uses_pbkdf2():
    """hash_password must produce salt$hash format (PBKDF2), not SHA-256 hex."""
    hashed = hash_password("securepassword")
    assert "$" in hashed, "PBKDF2 hash must contain salt separator"
    salt, hash_hex = hashed.split("$", 1)
    assert len(salt) == 32, "Salt must be 16 hex bytes (32 chars)"
    assert len(hash_hex) == 64, "PBKDF2 SHA-256 hash must be 64 hex chars"


@pytest.mark.skip(reason="Auth removed for local-only mode")
def test_verify_password_correct():
    """verify_password returns True for correct password."""
    hashed = hash_password("mypassword")
    assert verify_password("mypassword", hashed) is True


@pytest.mark.skip(reason="Auth removed for local-only mode")
def test_verify_password_incorrect():
    """verify_password returns False for incorrect password."""
    hashed = hash_password("mypassword")
    assert verify_password("wrongpassword", hashed) is False


@pytest.mark.skip(reason="User model removed for local-only mode")
@pytest.mark.asyncio
async def test_register_uses_pbkdf2_hash(client):
    pass


@pytest.mark.skip(reason="User model removed for local-only mode")
@pytest.mark.asyncio
async def test_login_with_correct_password(client):
    pass


@pytest.mark.skip(reason="User model removed for local-only mode")
@pytest.mark.asyncio
async def test_login_with_wrong_password(client):
    pass


@pytest.mark.asyncio
async def test_login_invalid_email_format(client):
    """Auth system removed — login endpoint should not exist (404)."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "not-an-email", "password": "password123"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_login_short_password(client):
    """Auth system removed — login endpoint should not exist (404)."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "short@example.com", "password": "short"},
    )
    assert resp.status_code == 404


# ── 3. API key ownership enforced ─────────────────────────────────────────


@pytest.mark.skip(reason="Auth removed for local-only mode")
@pytest.mark.asyncio
async def test_api_key_list_requires_auth(client):
    pass


@pytest.mark.skip(reason="User model removed for local-only mode")
@pytest.mark.asyncio
async def test_api_key_owned_by_user(client):
    pass


@pytest.mark.skip(reason="User model removed for local-only mode")
@pytest.mark.asyncio
async def test_delete_api_key_ownership_check(client):
    pass


@pytest.mark.skip(reason="User model removed for local-only mode")
@pytest.mark.asyncio
async def test_delete_own_api_key_succeeds(client):
    pass


# ── 4. User enumeration protected ─────────────────────────────────────────


@pytest.mark.skip(reason="User model removed for local-only mode")
@pytest.mark.asyncio
async def test_list_users_requires_admin(client):
    pass


@pytest.mark.skip(reason="User model removed for local-only mode")
@pytest.mark.asyncio
async def test_list_users_admin_allowed(client):
    pass


@pytest.mark.skip(reason="User model removed for local-only mode")
@pytest.mark.asyncio
async def test_switch_user_removed(client):
    pass


# ── 5. Settings uses authenticated user ──────────────────────────────────


@pytest.mark.skip(reason="User model removed for local-only mode")
@pytest.mark.asyncio
async def test_settings_uses_authenticated_user(client):
    pass


@pytest.mark.skip(reason="User model removed for local-only mode")
@pytest.mark.asyncio
async def test_settings_update_uses_authenticated_user(client):
    pass
