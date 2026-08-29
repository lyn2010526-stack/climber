"""Test configuration and fixtures."""

from __future__ import annotations

import asyncio
import os

# Set testing mode before importing app
os.environ["APP_TESTING"] = "true"
# Tests exercise the full API stack without real auth credentials;
# disable auth so integration/TestClient flows are deterministic.
os.environ["ENABLE_AUTH"] = "false"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.storage import Base, engine, init_db


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for all tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _create_tables_sync():
    """Create database tables synchronously."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(init_db())
        loop.run_until_complete(engine.dispose())
    finally:
        loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Ensure test database tables exist."""
    _create_tables_sync()
    yield


@pytest_asyncio.fixture(autouse=True)
async def cleanup_db(request):
    """Clean up database after each test."""
    yield
    if request.node.get_closest_marker("deployment_config"):
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
