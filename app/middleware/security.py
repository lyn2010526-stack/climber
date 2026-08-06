"""Security middleware — rate limiting, security headers, and input validation."""

from __future__ import annotations

import json
import secrets
from collections.abc import Awaitable, Callable
from ipaddress import ip_address, ip_network

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.storage.usage import usage_tracker

logger = structlog.get_logger(__name__)

MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
MAX_JSON_DEPTH = 10

CSRF_TOKEN_HEADER = "X-CSRF-Token"
CSRF_TOKEN_COOKIE = "csrf_token"
CSRF_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add comprehensive security headers to all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(
                "request_failed",
                path=request.url.path,
                error_type=type(exc).__name__,
            )
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "type": "internal_error"},
            )

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "object-src 'none'; "
            "media-src 'none'; "
            "worker-src 'none'; "
            "manifest-src 'self'; "
            "upgrade-insecure-requests"
        )
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=(), "
            "accelerometer=(), ambient-light-sensor=()"
        )
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"

        return response


class CsrfProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF protection using double-submit cookie pattern."""

    def __init__(
        self,
        app,
        excluded_paths: set[str] | None = None,
        enabled: bool = True,
    ):
        super().__init__(app)
        self.excluded_paths = excluded_paths or {
            "/health", "/health/logs", "/metrics",
            "/docs", "/openapi.json", "/favicon.ico",
        }
        self.enabled = enabled

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not self.enabled:
            return await call_next(request)

        path = request.url.path
        if path in self.excluded_paths:
            return await call_next(request)

        if request.method in CSRF_SAFE_METHODS:
            response = await call_next(request)
            if not request.cookies.get(CSRF_TOKEN_COOKIE):
                token = secrets.token_urlsafe(32)
                response.set_cookie(
                    key=CSRF_TOKEN_COOKIE,
                    value=token,
                    httponly=False,
                    samesite="strict",
                    secure=True,
                    max_age=3600,
                )
            return response

        cookie_token = request.cookies.get(CSRF_TOKEN_COOKIE)
        header_token = request.headers.get(CSRF_TOKEN_HEADER)

        if not cookie_token or not header_token:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing", "type": "csrf_error"},
            )

        if not secrets.compare_digest(cookie_token, header_token):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token mismatch", "type": "csrf_error"},
            )

        return await call_next(request)


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
    """Global rate limiting middleware with IP-based tracking."""

    SKIP_PATHS = {"/health", "/health/logs"}

    def __init__(self, app, trusted_proxies: list[str] | None = None):
        super().__init__(app)
        self.trusted_proxies = tuple(
            ip_network(proxy, strict=False) for proxy in (trusted_proxies or [])
        )

    def _is_trusted_proxy(self, host: str) -> bool:
        try:
            address = ip_address(host)
        except ValueError:
            return False
        return any(address in network for network in self.trusted_proxies)

    def _get_client_ip(self, request: Request) -> str:
        direct_ip = request.client.host if request.client else "unknown"
        if self._is_trusted_proxy(direct_ip):
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                candidate = forwarded.split(",", 1)[0].strip()
                try:
                    return str(ip_address(candidate))
                except ValueError:
                    pass
            real_ip = request.headers.get("X-Real-IP", "").strip()
            try:
                return str(ip_address(real_ip))
            except ValueError:
                pass
        if request.client:
            return direct_ip
        return "unknown"

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS" or request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        user_id = self._get_client_ip(request)

        allowed, reason = await usage_tracker.check_rate_limit(user_id)
        if not allowed:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={"detail": reason, "type": "rate_limit_exceeded"},
            )

        return await call_next(request)
