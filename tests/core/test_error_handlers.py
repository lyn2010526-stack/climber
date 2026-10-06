"""Tests for the global exception handlers and their error envelopes.

Builds a minimal FastAPI app, registers the shared handlers through
``register_exception_handlers``, and exercises each handler end-to-end so
the registration wiring itself is covered.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from app.core.error_handlers import (
    _classify_integrity_error,
    _describe_integrity_constraint,
    register_exception_handlers,
)
from app.core.exceptions import (
    AgentEngineError,
    AgentEngineHTTPError,
    ConflictException,
    NotFoundException,
    SessionNotFoundError,
)


class _EchoBody(BaseModel):
    name: str


_ORIG_MESSAGES: dict[str, Exception] = {
    "sqlite_not_null": Exception("NOT NULL constraint failed: users.name"),
    "sqlite_fk": Exception("FOREIGN KEY constraint failed"),
    "sqlite_unique": Exception("UNIQUE constraint failed: feedback.session_id, feedback.type"),
    "pg_not_null": Exception('null value in column "name" of relation "users" violates not-null constraint'),
    "pg_fk": Exception('insert or update on table "orders" violates foreign key constraint "orders_user_fkey"'),
    "pg_unique": Exception('duplicate key value violates unique constraint "feedback_pkey"'),
    "unknown": Exception("some unrecognized driver failure"),
}


def _build_app() -> FastAPI:
    """Build a minimal app with one route per handler under test."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/http-error")
    async def http_error() -> None:
        raise HTTPException(status_code=404, detail="missing", headers={"Cache-Control": "no-store"})

    @app.post("/validation-error")
    async def validation_error(body: _EchoBody) -> dict[str, str]:
        return {"name": body.name}

    @app.get("/app-not-found")
    async def app_not_found() -> None:
        raise NotFoundException("no such widget")

    @app.get("/app-conflict")
    async def app_conflict() -> None:
        raise ConflictException("already exists")

    @app.get("/engine-error")
    async def engine_error() -> None:
        raise SessionNotFoundError("session missing")

    @app.get("/engine-bridge-error")
    async def engine_bridge_error() -> None:
        raise AgentEngineHTTPError("engine blew up")

    @app.get("/integrity-error")
    async def integrity_error(kind: str = "unknown") -> None:
        raise IntegrityError("INSERT INTO ...", {}, _ORIG_MESSAGES[kind])

    @app.get("/unhandled")
    async def unhandled() -> None:
        raise RuntimeError("totally unexpected")

    return app


@pytest.fixture
def app() -> FastAPI:
    return _build_app()


async def _request(app: FastAPI, method: str, path: str, **kwargs: object):
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


async def test_http_exception_preserves_exc_headers(app: FastAPI) -> None:
    response = await _request(app, "GET", "/http-error")

    assert response.status_code == 404
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {"detail": "missing", "type": "http_error"}


async def test_request_validation_error_uses_validation_envelope(app: FastAPI) -> None:
    response = await _request(app, "POST", "/validation-error", json={"wrong": 1})

    assert response.status_code == 422
    body = response.json()
    assert body["type"] == "validation_error"
    assert isinstance(body["detail"], list)
    assert any("name" in str(error.get("loc")) for error in body["detail"])


async def test_base_app_exception_uses_its_status_and_type(app: FastAPI) -> None:
    not_found = await _request(app, "GET", "/app-not-found")
    conflict = await _request(app, "GET", "/app-conflict")

    assert not_found.status_code == 404
    assert not_found.json() == {"detail": "no such widget", "type": "not_found"}
    assert conflict.status_code == 409
    assert conflict.json() == {"detail": "already exists", "type": "conflict"}


async def test_agent_engine_error_bridges_to_agent_engine_envelope(app: FastAPI) -> None:
    response = await _request(app, "GET", "/engine-error")

    assert response.status_code == 500
    body = response.json()
    assert body["type"] == "agent_engine_error"
    assert body["detail"] == "Agent engine failure"
    assert body["type"] != "internal_error"


async def test_agent_engine_http_error_bridge_keeps_agent_engine_type(app: FastAPI) -> None:
    response = await _request(app, "GET", "/engine-bridge-error")

    assert response.status_code == 500
    assert response.json() == {"detail": "engine blew up", "type": "agent_engine_error"}


async def test_unhandled_exception_still_uses_generic_envelope(app: FastAPI) -> None:
    response = await _request(app, "GET", "/unhandled")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error", "type": "internal_error"}


@pytest.mark.parametrize(
    ("kind", "status_code", "error_type"),
    [
        ("sqlite_not_null", 422, "integrity_constraint"),
        ("pg_not_null", 422, "integrity_constraint"),
        ("sqlite_fk", 422, "integrity_constraint"),
        ("pg_fk", 422, "integrity_constraint"),
        ("sqlite_unique", 409, "integrity_conflict"),
        ("pg_unique", 409, "integrity_conflict"),
        ("unknown", 500, "persistence_error"),
    ],
)
async def test_integrity_error_is_classified_by_constraint_type(
    app: FastAPI, kind: str, status_code: int, error_type: str
) -> None:
    response = await _request(app, "GET", "/integrity-error", params={"kind": kind})

    assert response.status_code == status_code
    body = response.json()
    assert body["type"] == error_type
    assert "detail" in body


@pytest.mark.parametrize("kind", ["sqlite_not_null", "sqlite_unique", "pg_fk"])
async def test_integrity_error_response_does_not_leak_raw_constraint(app: FastAPI, kind: str) -> None:
    response = await _request(app, "GET", "/integrity-error", params={"kind": kind})

    assert "violates" not in response.text
    assert "users.name" not in response.text
    assert "INSERT INTO" not in response.text


def test_classify_integrity_error_covers_sqlite_and_postgres_messages() -> None:
    for kind, orig in _ORIG_MESSAGES.items():
        status_code, error_type, detail = _classify_integrity_error(orig)
        assert status_code in {409, 422, 500}
        assert error_type
        assert detail
        if kind in {"sqlite_not_null", "pg_not_null", "sqlite_fk", "pg_fk"}:
            assert (status_code, error_type) == (422, "integrity_constraint")


def test_classify_integrity_error_without_orig_falls_back_to_persistence() -> None:
    assert _classify_integrity_error(None) == (
        500,
        "persistence_error",
        "The request could not be persisted",
    )


@pytest.mark.parametrize(
    ("kind", "expected_identifier"),
    [
        ("sqlite_not_null", "users.name"),
        ("sqlite_unique", "feedback.session_id, feedback.type"),
        ("pg_unique", "feedback_pkey"),
        ("pg_fk", "orders_user_fkey"),
        ("pg_not_null", "name"),
        ("unknown", "some unrecognized driver failure"),
    ],
)
def test_describe_integrity_constraint_extracts_identifier(kind: str, expected_identifier: str) -> None:
    assert _describe_integrity_constraint(_ORIG_MESSAGES[kind]) == expected_identifier


def test_describe_integrity_constraint_handles_missing_orig() -> None:
    assert _describe_integrity_constraint(None) == "unknown"


def test_agent_engine_error_is_reachable_through_bridge_class() -> None:
    bridge = AgentEngineHTTPError("boom")

    assert isinstance(bridge, AgentEngineError)
    assert bridge.status_code == 500
    assert bridge.error_type == "agent_engine_error"
