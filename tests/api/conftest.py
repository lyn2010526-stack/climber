"""Shared fixtures for the HTTP-level API tests.

The repository-wide ``tests/conftest.py`` runs with ``ENABLE_AUTH=false``. Tests
that need the authenticated path flip ``settings.enable_auth`` on through the
``auth_on`` fixture, which also seeds an in-process emergency-stop manager so a
test that arms the kill switch can never leave it armed for the rest of the run.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.core import di
from app.core.auth_manager import create_access_token
from app.core.di import register as di_register
from app.core.observability import api as obs_api
from app.core.observability import emergency_stop as es
from app.main import app
from app.storage import engine as app_storage_engine


@pytest.fixture
def auth_on(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Enable authentication for the duration of one test."""
    monkeypatch.setattr(settings, "enable_auth", True)
    return


def bearer(subject: str, scopes: list[str] | None = None) -> dict[str, str]:
    """Return an Authorization header for a signed access token."""
    return {"Authorization": f"Bearer {create_access_token(subject, scopes or ['read', 'write'])}"}


def admin_bearer(subject: str = "admin-user") -> dict[str, str]:
    """Return an Authorization header carrying the admin scope."""
    return bearer(subject, ["read", "write", "admin"])


@pytest_asyncio.fixture
async def http() -> AsyncIterator[AsyncClient]:
    """A client bound to the real application, independent of auth settings."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def isolated_emergency_stop(tmp_path: Any) -> Iterator[None]:
    """Give each test a private emergency-stop store and a clean observability trio.

    The shared manager otherwise persists to ``data/emergency_stop.db``, so a test
    that arms the kill switch through the REST API would keep the engine blocked
    for every later test in the session.
    """
    original = es._EMERGENCY_STOP
    original_observability = (
        obs_api._trace_collector,
        obs_api._audit_chain,
        obs_api._goal_tracker,
    )
    es.set_emergency_stop(es.EmergencyStopManager(db_path=str(tmp_path / "stop.db")))
    obs_api._trace_collector = None
    obs_api._audit_chain = None
    obs_api._goal_tracker = None
    yield
    if es._EMERGENCY_STOP is not None:
        with __import__("contextlib").suppress(Exception):
            es._EMERGENCY_STOP.close()
    es.set_emergency_stop(original)
    obs_api._trace_collector, obs_api._audit_chain, obs_api._goal_tracker = (
        original_observability
    )


@pytest.fixture(autouse=True)
async def fresh_database_connections() -> AsyncIterator[None]:
    """Drop pooled async DB connections so no test inherits a stale read snapshot.

    SQLite runs in WAL mode, where a connection that stays idle-in-transaction
    keeps reading from the snapshot it started with. The repository-wide
    ``cleanup_db`` fixture wipes every table between tests on its own connection,
    so a pooled async connection carried into the next test can still see the
    deleted row: the SELECT in ``authenticate_user`` finds it and the UPDATE that
    follows then matches zero rows, surfacing as a 500 ``StaleDataError``. Closing
    the pool between tests removes the snapshot without touching production code.
    """
    await app_storage_engine.dispose()
    yield
    await app_storage_engine.dispose()


@pytest.fixture(autouse=True)
def isolated_rate_limit(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Start every test with an empty rate-limit window.

    ``RateLimitMiddleware`` keys its sliding window on the principal or client IP,
    which is constant for the in-process ASGI transport, so the counters otherwise
    carry over between tests and unrelated requests start returning 429.
    ``UsageTracker.reset`` is the seam the tracker documents for exactly this, and
    the window is opened up because several of these tests deliberately drive more
    than the production 30 requests/minute to exercise a full lifecycle.
    """
    from app.storage.usage import usage_tracker

    usage_tracker.reset()
    monkeypatch.setattr(usage_tracker, "requests_per_minute", 10_000)
    yield
    usage_tracker.reset()


@pytest.fixture(autouse=True)
def registered_core_services() -> Iterator[None]:
    """Register the DI services the app resolves at request time.

    ``app.main.lifespan`` performs these registrations in production, but the
    ASGI test client does not run the lifespan, so without them every request that
    reaches ``get_engine()`` dies in ``di_resolve`` and surfaces as a 500. This
    mirrors ``_register_core_services`` rather than stubbing the engine out.
    """
    from app.models.registry import ModelRegistry
    from app.tools import tool_registry as global_tool_registry

    original_container = dict(di._container)
    original_factories = dict(di._factories)
    di_register("ModelRegistry", ModelRegistry())
    di_register("ToolRegistry", global_tool_registry)
    try:
        yield
    finally:
        di._container.clear()
        di._container.update(original_container)
        di._factories.clear()
        di._factories.update(original_factories)


@pytest.fixture
def workflow_runtime() -> Iterator[None]:
    """Kept as an explicit opt-in name; ``registered_core_services`` is autouse."""
    return
