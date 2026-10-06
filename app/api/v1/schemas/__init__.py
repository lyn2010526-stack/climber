"""Shared response schema package for API v1 route handlers."""

from __future__ import annotations

from app.api.v1.schemas.response import ApiResponse, ErrorResponse, PaginatedResponse

__all__ = ["ApiResponse", "ErrorResponse", "PaginatedResponse"]
