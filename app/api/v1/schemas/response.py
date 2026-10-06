"""Unified response envelope models for API v1 route handlers.

These generic models give route handlers a consistent response shape to
opt into. Existing endpoints that already return plain dicts are not
required to migrate; new endpoints and refactors should prefer these
types for consistency.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Generic success envelope wrapping a single payload value.

    Attributes:
        ok: Always True for a successful response.
        data: The payload returned by the endpoint.
    """

    model_config = ConfigDict(extra="ignore")

    ok: bool = True
    data: T


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic success envelope wrapping a page of list results.

    Attributes:
        ok: Always True for a successful response.
        items: The page of items returned by the endpoint.
        total: Total number of items available across all pages.
        limit: The page size that was applied.
        offset: The number of items skipped before this page.
    """

    model_config = ConfigDict(extra="ignore")

    ok: bool = True
    items: list[T]
    total: int
    limit: int
    offset: int = 0


class ErrorResponse(BaseModel):
    """Generic error envelope for non-2xx responses.

    Attributes:
        ok: Always False for an error response.
        detail: Human-readable error message.
        type: Machine-readable error category (e.g. "not_found", "validation_error").
    """

    model_config = ConfigDict(extra="ignore")

    ok: bool = False
    detail: str
    type: str = "error"
