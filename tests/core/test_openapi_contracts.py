"""Regression tests for the public API contract exposed through OpenAPI."""

from __future__ import annotations

from app.main import app


def test_openapi_declares_versioned_metadata_and_response_models() -> None:
    schema = app.openapi()

    assert schema["info"]["version"] == "0.2.0"
    assert schema["paths"]["/api/v1/workflows"]["get"]["responses"]["200"]["content"]
    assert schema["paths"]["/api/v1/workflows"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["type"] == "array"
    assert schema["paths"]["/api/v1/settings/"]["get"]["responses"]["200"]["content"]
    assert "workflows" in {tag["name"] for tag in schema["tags"]}


def test_openapi_declares_resource_response_models() -> None:
    schema = app.openapi()

    for path in (
        "/api/v1/groups",
        "/api/v1/crews",
        "/api/v1/skills",
        "/api/v1/scheduler/tasks",
    ):
        response = schema["paths"][path]["get"]["responses"]["200"]
        assert response["content"]["application/json"]["schema"]
