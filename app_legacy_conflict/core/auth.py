"""Local-user identity shared by API endpoints."""

from __future__ import annotations

LOCAL_USER_ID = "default-user"


def get_current_user() -> str:
    """Return the single local user used by this local-first application."""
    return LOCAL_USER_ID
