"""Shared helpers for API v1 endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import Request

DEFAULT_USER = "default-user"


async def payload(request: Request) -> dict[str, Any]:
    """Read a JSON body tolerantly: flat object or {"data": {...}} envelope."""
    try:
        raw = await request.json()
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    inner = raw.get("data")
    if isinstance(inner, dict):
        return inner
    return raw