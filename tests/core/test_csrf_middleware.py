"""Regression tests for CSRF wiring and header-authenticated clients."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import app as production_app
from app.middleware.security import CsrfProtectionMiddleware


def _app() -> FastAPI:
    test_app = FastAPI()
    test_app.add_middleware(CsrfProtectionMiddleware)

    @test_app.get("/resource")
    async def get_resource() -> dict[str, str]:
        return {"status": "ok"}

    @test_app.post("/resource")
    async def post_resource() -> dict[str, str]:
        return {"status": "updated"}

    return test_app


@pytest.mark.asyncio
async def test_cookie_authenticated_write_requires_matching_csrf_token() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=_app()),
        base_url="https://test",
    ) as client:
        response = await client.get("/resource")
        token = response.cookies.get("csrf_token")

        assert response.status_code == 200
        assert token
        assert (await client.post("/resource")).status_code == 403
        assert (
            await client.post("/resource", headers={"X-CSRF-Token": "wrong"})
        ).status_code == 403
        assert (await client.post("/resource", headers={"X-CSRF-Token": token})).status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "headers",
    [
        {"X-API-Key": "ae_test-token"},
        {"Authorization": "Bearer test-token"},
    ],
)
async def test_header_authenticated_writes_remain_csrf_compatible(
    headers: dict[str, str],
) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=_app()),
        base_url="https://test",
    ) as client:
        response = await client.post("/resource", headers=headers)

    assert response.status_code == 200


def test_production_registers_csrf_before_authentication_chain() -> None:
    execution_order = [
        middleware.cls.__name__ for middleware in reversed(production_app.user_middleware)
    ]

    assert (
        execution_order.index("RequestValidationMiddleware")
        < execution_order.index("CsrfProtectionMiddleware")
        < execution_order.index("RateLimitMiddleware")
        < execution_order.index("AuthMiddleware")
    )
