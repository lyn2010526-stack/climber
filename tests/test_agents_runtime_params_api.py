"""API tests for agent runtime sampling parameter persistence.

Verifies that ``temperature`` and ``max_tokens`` are accepted on agent
creation, stored on the ``agents`` row, and echoed back through create/list/get
responses.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_create_persists_runtime_params(client) -> None:
    response = await client.post(
        "/api/v1/agents",
        json={
            "name": "runtime-param-agent",
            "provider": "openai",
            "model_id": "gpt-4o-mini",
            "temperature": 0.4,
            "max_tokens": 2048,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["temperature"] == pytest.approx(0.4)
    assert body["max_tokens"] == 2048


@pytest.mark.asyncio
async def test_list_and_get_echo_runtime_params(client) -> None:
    response = await client.post(
        "/api/v1/agents",
        json={"name": "runtime-param-agent", "temperature": 0.4, "max_tokens": 2048},
    )
    assert response.status_code == 200, response.text
    agent_id = response.json()["id"]

    listed = await client.get("/api/v1/agents")
    assert listed.status_code == 200
    match = [a for a in listed.json() if a["id"] == agent_id]
    assert match and match[0]["temperature"] == pytest.approx(0.4)
    assert match[0]["max_tokens"] == 2048

    got = await client.get(f"/api/v1/agents/{agent_id}")
    assert got.status_code == 200
    assert got.json()["temperature"] == pytest.approx(0.4)
    assert got.json()["max_tokens"] == 2048


@pytest.mark.asyncio
async def test_default_temperature_used_when_omitted(client) -> None:
    response = await client.post(
        "/api/v1/agents",
        json={"name": "default-temp-agent", "max_tokens": 1024},
    )
    assert response.status_code == 200, response.text
    assert response.json()["temperature"] == pytest.approx(0.7)
    assert response.json()["max_tokens"] == 1024


@pytest.mark.asyncio
async def test_invalid_temperature_rejected(client) -> None:
    response = await client.post(
        "/api/v1/agents",
        json={"name": "bad-temp-agent", "temperature": 3.0},
    )
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_non_positive_max_tokens_rejected(client) -> None:
    response = await client.post(
        "/api/v1/agents",
        json={"name": "bad-tokens-agent", "max_tokens": 0},
    )
    assert response.status_code == 422, response.text
