"""Rate limiting middleware and dependency."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from app.storage.auth import get_current_user
from app.storage.usage import usage_tracker


class RateLimiter:
    """FastAPI dependency that enforces rate limits."""

    def __init__(self, user_id: str = Depends(get_current_user)):
        self.user_id = user_id

    async def __call__(self, request: Request) -> None:
        # Skip rate limiting for health check and auth endpoints
        if request.url.path in ("/health", "/api/v1/auth/register", "/api/v1/auth/login"):
            return

        allowed, reason = await usage_tracker.check_rate_limit(self.user_id)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=reason,
            )


RateLimit = Depends(RateLimiter)
