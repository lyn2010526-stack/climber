"""Strict API v1 request and response schemas.

Response envelope types are re-exported from
``app.api.v1.schemas.response`` so route and test code can use one
canonical definition regardless of which package path it imports.
"""

from __future__ import annotations

from app.api.v1.schemas.response import ApiResponse, ErrorResponse, PaginatedResponse

__all__ = ["ApiResponse", "ErrorResponse", "PaginatedResponse"]
