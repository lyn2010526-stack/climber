"""Rate limiting middleware and dependency."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from app.core.principal import CurrentPrincipal
from app.storage.usage import usage_tracker


class RateLimiter:
    """FastAPI dependency that enforces rate limits."""

    async def __call__(self, request: Request, principal: CurrentPrincipal) -> None:
        del request
        allowed, reason = await usage_tracker.check_rate_limit(principal.identity_key)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=reason,
            )


RateLimit = Depends(RateLimiter)
