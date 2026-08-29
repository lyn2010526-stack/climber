"""Shared helpers for API v1 endpoints.

Compatibility facade over ``app.api.v1._shared``: the canonical payload
envelope reader and default user id live in ``_shared`` and are re-exported
here so older imports keep working.
"""

from __future__ import annotations

from app.api.v1._shared import DEFAULT_USER
from app.api.v1._shared import _payload as payload

__all__ = ["DEFAULT_USER", "payload"]
