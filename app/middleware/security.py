"""Security middleware — rate limiting, security headers, and input validation."""

from __future__ import annotations

import json

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.storage.usage import usage_tracker

MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
MAX_JSON_DEPTH = 10


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


def _check_json_depth(obj, depth: int = 0) -> bool:
    """Return True if JSON depth exceeds MAX_JSON_DEPTH."""
    if depth > MAX_JSON_DEPTH:
        return False
    if isinstance(obj, dict):
        return all(_check_json_depth(v, depth + 1) for v in obj.values())
    if isinstance(obj, list):
        return all(_check_json_depth(item, depth + 1) for item in obj)
    return True


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Validate request size and JSON depth."""

    SKIP_PATHS = {"/health", "/health/logs", "/metrics"}

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_CONTENT_LENGTH:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large", "max_bytes": MAX_CONTENT_LENGTH},
            )

        if request.method in ("POST", "PUT", "PATCH") and request.headers.get("content-type", "").startswith("application/json"):
            try:
                body = await request.body()
                if body:
                    data = json.loads(body)
                    if not _check_json_depth(data):
                        from fastapi.responses import JSONResponse
                        return JSONResponse(
                            status_code=400,
                            content={"detail": f"JSON nesting exceeds maximum depth of {MAX_JSON_DEPTH}"},
                        )
            except json.JSONDecodeError:
                pass

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Global rate limiting middleware."""

    SKIP_PATHS = {
        "/health", "/health/logs", "/metrics", "/api/v1/terminal/health",
    }

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        user_id = "default-user"

        allowed, reason = await usage_tracker.check_rate_limit(user_id)
        if not allowed:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={"detail": reason, "type": "rate_limit_exceeded"},
            )

        await usage_tracker.record_request(user_id)
        return await call_next(request)
