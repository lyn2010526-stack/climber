"""Schema alignment tests for the unified API v1 response envelope."""

from __future__ import annotations

from app.api.v1.common import error_response, ok_response, success_response
from app.api.v1.schemas import ApiResponse, ErrorResponse, PaginatedResponse
from app.api.v1.schemas.response import ApiResponse as RouteApiResponse
from app.schemas.api_v1 import ApiResponse as CompatApiResponse
from app.schemas.api_v1.agents import AgentCreateRequest, AgentResponse
from app.schemas.api_v1.base import PublicResponse, StrictRequest


def test_api_response_serializes_to_ok_data_envelope() -> None:
    response = success_response({"id": "agent-1"})

    assert isinstance(response, ApiResponse)
    assert response.model_dump() == {"ok": True, "data": {"id": "agent-1"}}


def test_api_response_ignores_extra_fields() -> None:
    response = ApiResponse[dict[str, str]].model_validate(
        {"ok": True, "data": {"id": "agent-1"}, "legacy_extra": "ignored"}
    )

    assert response.model_dump() == {"ok": True, "data": {"id": "agent-1"}}


def test_paginated_response_serializes_paging_fields() -> None:
    response = PaginatedResponse[dict[str, str]](
        items=[{"id": "agent-1"}, {"id": "agent-2"}],
        total=12,
        limit=2,
        offset=10,
    )

    assert response.model_dump() == {
        "ok": True,
        "items": [{"id": "agent-1"}, {"id": "agent-2"}],
        "total": 12,
        "limit": 2,
        "offset": 10,
    }


def test_paginated_response_default_offset() -> None:
    response = PaginatedResponse[int](items=[], total=0, limit=20)

    assert response.offset == 0


def test_error_response_serializes_to_ok_detail_type_envelope() -> None:
    response = error_response("Agent not found", "not_found")

    assert isinstance(response, ErrorResponse)
    assert response.model_dump() == {
        "ok": False,
        "detail": "Agent not found",
        "type": "not_found",
    }


def test_error_response_default_error_type() -> None:
    response = ErrorResponse(detail="unexpected failure")

    assert response.model_dump() == {
        "ok": False,
        "detail": "unexpected failure",
        "type": "error",
    }


def test_error_response_ignores_extra_fields() -> None:
    response = ErrorResponse.model_validate(
        {"detail": "missing", "type": "not_found", "legacy_extra": "ignored"}
    )

    assert response.model_dump() == {"ok": False, "detail": "missing", "type": "not_found"}


def test_ok_response_preserves_legacy_deletion_shape() -> None:
    assert ok_response("agent-1") == {"ok": True, "deleted": "agent-1"}


def test_old_schema_package_reexports_unified_classes() -> None:
    assert CompatApiResponse is ApiResponse
    assert RouteApiResponse is ApiResponse


def test_old_schema_modules_remain_importable() -> None:
    assert AgentCreateRequest.__name__ == "AgentCreateRequest"
    assert AgentResponse.__name__ == "AgentResponse"
    assert PublicResponse.__name__ == "PublicResponse"
    assert StrictRequest.__name__ == "StrictRequest"
