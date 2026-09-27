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
