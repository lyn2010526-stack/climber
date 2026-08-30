from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1 import channels
from app.api.v1 import router as api_v1_router
from app.core.auth import get_current_user
from app.core.channel_gateway import ChannelGateway


@pytest.fixture
def gateway(monkeypatch: pytest.MonkeyPatch) -> ChannelGateway:
    instance = ChannelGateway(dm_enabled=True)
    monkeypatch.setattr(channels, "get_channel_gateway", lambda: instance)
    return instance


@pytest_asyncio.fixture
async def pairing_client(gateway: ChannelGateway):
    app = FastAPI()
    app.include_router(channels.router, prefix="/api/v1/channels")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield app, client


async def create_pending(gateway: ChannelGateway, owner_user_id: str = "default-user"):
    await gateway.authorize(
        channel="telegram",
        external_user_id="user-1",
        conversation_id="chat-1",
        chat_type="private",
        owner_user_id=owner_user_id,
    )
    return (await gateway.list_pairings(owner_user_id=owner_user_id))[0]


@pytest.mark.asyncio
async def test_list_and_approve_pending_pairing(pairing_client, gateway):
    _, client = pairing_client
    pairing = await create_pending(gateway)

    listed = await client.get("/api/v1/channels/pairings?status=pending")
    approved = await client.post(f"/api/v1/channels/pairings/{pairing.id}/approve")

    assert listed.status_code == 200
    assert listed.json()["pairings"][0]["capability"] == "dm:chat"
    assert approved.status_code == 200
    assert approved.json()["pairing"]["status"] == "paired"


@pytest.mark.asyncio
async def test_revoke_pairing(pairing_client, gateway):
    _, client = pairing_client
    pairing = await create_pending(gateway)
    await gateway.approve(pairing.id, owner_user_id="default-user")

    response = await client.post(f"/api/v1/channels/pairings/{pairing.id}/revoke")

    assert response.status_code == 200
    assert response.json()["pairing"]["status"] == "revoked"


@pytest.mark.asyncio
async def test_pairing_api_is_isolated_by_current_user(pairing_client, gateway):
    app, client = pairing_client
    pairing = await create_pending(gateway, owner_user_id="owner-a")
    app.dependency_overrides[get_current_user] = lambda: "owner-b"
    try:
        listed = await client.get("/api/v1/channels/pairings")
        approved = await client.post(f"/api/v1/channels/pairings/{pairing.id}/approve")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert listed.status_code == 200
    assert listed.json() == {"pairings": [], "total": 0}
    assert approved.status_code == 404
    assert approved.json()["detail"]["code"] == "PAIRING_NOT_FOUND"


def test_pairing_router_reuses_current_user_dependency():
    dependencies = [getattr(dependency, "dependency", None) for dependency in channels.router.dependencies]

    assert get_current_user in dependencies


def test_pairing_router_is_reachable_from_api_v1_aggregator():
    assert str(api_v1_router.url_path_for("list_pairings")) == "/channels/pairings"
