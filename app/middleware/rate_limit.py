"""Rate limiting middleware and dependency."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from app.storage.usage import usage_tracker


class RateLimiter:
    """FastAPI dependency that enforces rate limits."""

    def __init__(self):
        self.user_id = "default-user"

    async def __call__(self, request: Request) -> None:
        allowed, reason = await usage_tracker.check_rate_limit(self.user_id)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=reason,
            )


RateLimit = Depends(RateLimiter)
