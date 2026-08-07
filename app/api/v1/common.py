"""Shared utilities for API route handlers.

Provides common request parsing, database query helpers, and response formatting
functions used across all route modules.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TypeVar

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase

from app.core.principal import LOCAL_SUBJECT_ID, get_context_principal

DEFAULT_USER: str = LOCAL_SUBJECT_ID

T = TypeVar("T", bound=DeclarativeBase)

_SENSITIVE_RESPONSE_FIELDS = {"api_key", "api_key_encrypted", "env", "environment"}


def current_user_id(request: Request) -> str:
    """Compatibility proxy for handlers migrating to CurrentPrincipal."""
    del request
    try:
        return get_context_principal().subject_id
    except RuntimeError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


async def parse_request_payload(request: Request) -> dict[str, Any]:
    """Parse JSON body tolerantly: accepts flat object or {"data": {...}} envelope.

    Args:
        request: The incoming FastAPI request object.

    Returns:
        A dictionary containing the parsed payload data.
    """
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


async def get_or_404(
    db: Any,
    model: type[T],
    entity_id: str,
    *,
    detail: str | None = None,
) -> T:
    """Fetch a database entity by ID or raise a 404 HTTPException.

    Args:
        db: The async database session.
        model: The SQLAlchemy model class to query.
        entity_id: The primary key ID to look up.
        detail: Optional custom error message. Defaults to "{Model} not found".

    Returns:
        The database entity instance.

    Raises:
        HTTPException: 404 if the entity is not found.
    """
    result = (await db.execute(select(model).where(model.id == entity_id))).scalar_one_or_none()
    if result is None:
        raise HTTPException(status_code=404, detail=detail or f"{model.__name__} not found")
    return result


def entities_to_dicts(entities: Sequence[T], dict_fn: callable) -> list[dict[str, Any]]:
    """Convert a sequence of database entities to dictionaries using a mapping function.

    Args:
        entities: A sequence of SQLAlchemy model instances.
        dict_fn: A callable that converts a single entity to a dictionary.

    Returns:
        A list of dictionaries representing the entities.
    """
    return [dict_fn(e) for e in entities]


def ok_response(deleted: str) -> dict[str, bool | str]:
    """Create a standard deletion success response.

    Args:
        deleted: The ID of the deleted entity.

    Returns:
        A dictionary with 'ok' and 'deleted' keys.
    """
    return {"ok": True, "deleted": deleted}


def redact_sensitive_fields(value: Any) -> Any:
    """Recursively remove credentials and environment data from API responses."""
    if isinstance(value, dict):
        return {
            key: redact_sensitive_fields(item)
            for key, item in value.items()
            if key.lower() not in _SENSITIVE_RESPONSE_FIELDS
        }
    if isinstance(value, list):
        return [redact_sensitive_fields(item) for item in value]
    return value
