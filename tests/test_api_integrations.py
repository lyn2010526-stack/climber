"""Regression tests for optional integration API behavior."""

from __future__ import annotations

from unittest.mock import patch


async def test_langgraph_invoke_reports_missing_optional_dependency_as_client_error(client) -> None:
    with patch.dict("sys.modules", {"langgraph": None}):
        response = await client.post(
            "/api/v1/integrations/langgraph/probe/invoke",
            json={"inputs": {}},
        )

    assert response.status_code == 424
    assert "LangGraph runtime is not installed" in response.json()["detail"]


async def test_mem0_search_reports_missing_optional_dependency_as_client_error(client) -> None:
    with patch.dict("sys.modules", {"mem0": None}):
        response = await client.post(
            "/api/v1/integrations/mem0/search",
            json={"query": "probe"},
        )

    assert response.status_code == 424
    assert "Mem0 runtime is not installed" in response.json()["detail"]


async def test_mem0_add_reports_missing_optional_dependency_as_client_error(client) -> None:
    with patch.dict("sys.modules", {"mem0": None}):
        response = await client.post(
            "/api/v1/integrations/mem0/add",
            json={"content": "probe"},
        )

    assert response.status_code == 424
    assert "Mem0 runtime is not installed" in response.json()["detail"]
