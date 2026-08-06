"""Authenticated identity shared by API endpoints."""

from __future__ import annotations

from fastapi import HTTPException, Request

from app.config import settings

LOCAL_USER_ID = "default-user"


def get_current_user(request: Request) -> str:
    """Return the authenticated user ID, or the local user when auth is disabled."""
    if not settings.enable_auth:
        return LOCAL_USER_ID

    auth = getattr(request.state, "auth", None)
    if isinstance(auth, dict):
        for field in ("user_id", "id", "sub", "owner"):
            value = auth.get(field)
            if value is not None and str(value):
                return str(value)

    raise HTTPException(status_code=401, detail="Authenticated user identity is missing")
