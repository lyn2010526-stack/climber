"""Authenticated principal and request-scoped identity propagation."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request

from app.config import settings

LOCAL_SUBJECT_ID = "default-user"


@dataclass(frozen=True, slots=True)
class Principal:
    """Identity and authorization attributes for the current caller."""

    subject_id: str
    tenant_id: str | None = None
    role: str | None = None
    scopes: tuple[str, ...] = ()
    auth_method: str = "local"

    @property
    def identity_key(self) -> str:
        """Return a stable rate-limit and audit identity."""
        tenant = self.tenant_id or "default"
        return f"{self.auth_method}:{tenant}:{self.subject_id}"


principal_context: ContextVar[Principal | None] = ContextVar("principal_context", default=None)


def set_current_principal(principal: Principal) -> Token[Principal | None]:
    """Set the principal for downstream execution and return its reset token."""
    return principal_context.set(principal)


def reset_current_principal(token: Token[Principal | None]) -> None:
    """Restore the principal context to its previous value."""
    principal_context.reset(token)


def get_context_principal() -> Principal:
    """Resolve an explicitly propagated principal, with local-only fallback."""
    principal = principal_context.get()
    if principal is not None:
        return principal
    if not settings.enable_auth:
        return Principal(subject_id=LOCAL_SUBJECT_ID)
    raise RuntimeError("Authenticated principal context is missing")


def _first_identity(auth: dict[str, Any]) -> str | None:
    for field in ("user_id", "id", "sub", "owner"):
        value = auth.get(field)
        if value is not None and str(value):
            return str(value)
    return None


async def get_current_principal(request: Request) -> AsyncIterator[Principal]:
    """Build and propagate the caller principal from authentication state."""
    if not settings.enable_auth:
        principal = Principal(subject_id=LOCAL_SUBJECT_ID)
    else:
        auth = getattr(request.state, "auth", None)
        if not isinstance(auth, dict):
            raise HTTPException(status_code=401, detail="Authenticated principal is missing")

        subject_id = _first_identity(auth)
        if subject_id is None:
            raise HTTPException(status_code=401, detail="Authenticated user identity is missing")

        raw_scopes = auth.get("scopes") or ()
        if isinstance(raw_scopes, str):
            raw_scopes = raw_scopes.split()
        principal = Principal(
            subject_id=subject_id,
            tenant_id=str(auth["tenant_id"]) if auth.get("tenant_id") is not None else None,
            role=str(auth["role"]) if auth.get("role") is not None else None,
            scopes=tuple(str(scope) for scope in raw_scopes),
            auth_method=str(auth.get("method") or "authenticated"),
        )

    token = set_current_principal(principal)
    try:
        yield principal
    finally:
        reset_current_principal(token)


CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]
