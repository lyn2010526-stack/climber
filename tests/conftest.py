"""Test configuration and fixtures."""

from __future__ import annotations

import os
import asyncio

# Set testing mode before importing app
os.environ["APP_TESTING"] = "true"

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.storage import init_db, engine, async_session, Base
from app.storage.database import Agent, Session, Message, ApiKey, Tool, Document, CheckpointRecord
from app.storage import models_memory


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
    """Clean up database after each test."""
    yield
    import asyncio
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
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
