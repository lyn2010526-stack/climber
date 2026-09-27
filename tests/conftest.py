"""Test configuration and fixtures."""

from __future__ import annotations

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
from app.storage import Base, engine, init_db
from app.storage.usage import usage_tracker


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for all tests."""
    import asyncio

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
    return


@pytest_asyncio.fixture(autouse=True)
async def cleanup_db():
    """Clean up database after each test by deleting data from tables."""
    import contextlib

    from sqlalchemy.exc import OperationalError

    async def _clear() -> None:
        # Dispose pooled connections before deleting rows. SQLite WAL
        # connections can retain a read snapshot across test boundaries.
        await engine.dispose()
        async with engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                with contextlib.suppress(OperationalError):
                    await conn.execute(table.delete())
            await conn.commit()
        await engine.dispose()

    await _clear()
    yield
    await _clear()


@pytest.fixture(autouse=True)
def reset_usage_tracker():
    """Reset the in-process usage tracker so rate-limit counts do not leak across tests."""
    yield
    usage_tracker.reset()


@pytest.fixture(autouse=True)
def isolate_environment():
    """Restore process environment changes after every test."""
    original = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original)


@pytest.fixture(autouse=True)
def reset_network_gate():
    """Restore the network egress gate after every test.

    The gate is class-level state on ToolRegistry, so a test that disables it
    would otherwise leave egress closed for the rest of the session and make
    later failures depend on test ordering.
    """
    from app.tools import ToolRegistry

    original = ToolRegistry.network_enabled()
    yield
    ToolRegistry.set_network_enabled(original)


@pytest.fixture(autouse=True)
def reset_emergency_stop_manager():
    """Restore the process-wide emergency-stop manager after every test."""
    from app.core.observability import emergency_stop

    original = emergency_stop._EMERGENCY_STOP
    yield
    emergency_stop._EMERGENCY_STOP = original


@pytest_asyncio.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
