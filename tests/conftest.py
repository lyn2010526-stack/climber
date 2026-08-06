"""Test configuration and fixtures."""

from __future__ import annotations

import asyncio
import os

# Set testing mode before importing app
os.environ["APP_TESTING"] = "true"
# Tests assume authentication is disabled by default; the repo .env may
# enable it for local dev, so pin it off for the test run.
os.environ["ENABLE_AUTH"] = "false"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from sqlalchemy import text
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
    finally:
        loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Ensure test database tables exist."""
    _create_tables_sync()
    yield


@pytest.fixture(autouse=True)
def cleanup_db():
    """Clean up database after each test by deleting data from tables."""
    yield
    import asyncio
    from sqlalchemy.exc import OperationalError
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        async def _cleanup():
            async with engine.begin() as conn:
                for table in reversed(Base.metadata.sorted_tables):
                    try:
                        await conn.execute(text(f"DELETE FROM {table.name}"))
                    except OperationalError:
                        pass  # Table may not exist
                await conn.commit()
        loop.run_until_complete(_cleanup())
    finally:
        loop.close()


@pytest_asyncio.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
