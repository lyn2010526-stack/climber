"""Middleware: rate_limiting - API rate limiting."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import datetime

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = structlog.get_logger()


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """API rate limiting middleware."""

    def __init__(
        self,
        app: ASGIApp,
        enabled: bool = True,
        exclude_paths: list[str] | None = None,
        **kwargs,
    ):
        super().__init__(app)
        self.enabled = enabled
        self.exclude_paths = exclude_paths or []
        self._request_counts: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Process request through middleware."""
        if not self.enabled:
            return await call_next(request)

        path = request.url.path
        for exclude in self.exclude_paths:
            if path.startswith(exclude):
                return await call_next(request)

        start_time = time.time()
        request_id = str(uuid.uuid4())

        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=path,
            method=request.method,
        )

        try:
            response = await call_next(request)
            duration = (time.time() - start_time) * 1000

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{duration:.2f}ms"

            logger.info(
                "Request processed",
                status_code=response.status_code,
                duration_ms=duration,
            )
            return response
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error("Request failed", error=str(e), duration_ms=duration)
            raise
        finally:
            structlog.contextvars.clear_contextvars()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""

    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 60,
        burst_size: int = 10,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _is_rate_limited(self, client_id: str) -> bool:
        """Check if client is rate limited."""
        now = time.time()
        minute_ago = now - 60

        self._requests[client_id] = [
            t for t in self._requests[client_id] if t > minute_ago
        ]

        if len(self._requests[client_id]) >= self.requests_per_minute:
            return True

        self._requests[client_id].append(now)
        return False

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Apply rate limiting."""
        client_id = request.client.host if request.client else "unknown"

        if self._is_rate_limited(client_id):
            return Response(
                content='{"error": "Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "60"},
            )

        return await call_next(request)


class CacheMiddleware(BaseHTTPMiddleware):
    """Response caching middleware."""

    def __init__(
        self,
        app: ASGIApp,
        default_ttl: int = 300,
        max_size: int = 1000,
    ):
        super().__init__(app)
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._cache: dict[str, tuple[bytes, str, float]] = {}

    def _get_cache_key(self, request: Request) -> str:
        """Generate cache key from request."""
        return f"{request.method}:{request.url.path}:{request.url.query}"

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Apply caching."""
        if request.method != "GET":
            return await call_next(request)

        key = self._get_cache_key(request)
        if key in self._cache:
            body, content_type, expires = self._cache[key]
            if time.time() < expires:
                return Response(content=body, media_type=content_type, headers={"X-Cache": "HIT"})

        response = await call_next(request)

        if response.status_code == 200 and len(self._cache) < self.max_size:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            self._cache[key] = (body, response.media_type or "application/json", time.time() + self.default_ttl)
            return Response(content=body, media_type=response.media_type, headers={"X-Cache": "MISS"})

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Structured logging middleware."""

    def __init__(
        self,
        app: ASGIApp,
        log_body: bool = False,
        log_headers: bool = False,
        exclude_paths: list[str] | None = None,
    ):
        super().__init__(app)
        self.log_body = log_body
        self.log_headers = log_headers
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Log request and response."""
        path = request.url.path
        start_time = time.time()

        if path not in self.exclude_paths:
            logger.info(
                "Request started",
                method=request.method,
                path=path,
                query=str(request.url.query),
                client=request.client.host if request.client else "unknown",
            )

        response = await call_next(request)
        duration = (time.time() - start_time) * 1000

        if path not in self.exclude_paths:
            logger.info(
                "Request completed",
                method=request.method,
                path=path,
                status_code=response.status_code,
                duration_ms=f"{duration:.2f}",
            )

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    def __init__(self, app: ASGIApp, custom_headers: dict[str, str] | None = None):
        super().__init__(app)
        self.custom_headers = custom_headers or {}

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Add security headers."""
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        for key, value in self.custom_headers.items():
            response.headers[key] = value

        return response


class CORSMiddleware(BaseHTTPMiddleware):
    """CORS middleware with configurable options."""

    def __init__(
        self,
        app: ASGIApp,
        allow_origins: list[str] | None = None,
        allow_methods: list[str] | None = None,
        allow_headers: list[str] | None = None,
        allow_credentials: bool = True,
        max_age: int = 86400,
    ):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["*"]
        self.allow_headers = allow_headers or ["*"]
        self.allow_credentials = allow_credentials
        self.max_age = max_age

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Handle CORS."""
        origin = request.headers.get("origin", "")

        if request.method == "OPTIONS":
            headers = {}
            if origin in self.allow_origins or "*" in self.allow_origins:
                headers["Access-Control-Allow-Origin"] = origin if origin else "*"
                headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
                headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
                headers["Access-Control-Max-Age"] = str(self.max_age)
                if self.allow_credentials:
                    headers["Access-Control-Allow-Credentials"] = "true"
            return Response(status_code=204, headers=headers)

        response = await call_next(request)

        if origin in self.allow_origins or "*" in self.allow_origins:
            response.headers["Access-Control-Allow-Origin"] = origin if origin else "*"
            if self.allow_credentials:
                response.headers["Access-Control-Allow-Credentials"] = "true"

        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Validate incoming requests."""

    def __init__(
        self,
        app: ASGIApp,
        max_body_size: int = 10 * 1024 * 1024,
        required_headers: list[str] | None = None,
    ):
        super().__init__(app)
        self.max_body_size = max_body_size
        self.required_headers = required_headers or []

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Validate request."""
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_size:
            return Response(
                content='{"error": "Request body too large"}',
                status_code=413,
                media_type="application/json",
            )

        for header in self.required_headers:
            if not request.headers.get(header):
                return Response(
                    content=f'{{"error": "Missing required header: {header}"}}',
                    status_code=400,
                    media_type="application/json",
                )

        return await call_next(request)


class TimingMiddleware(BaseHTTPMiddleware):
    """Add timing information to responses."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Measure request timing."""
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        response.headers["X-Response-Time"] = f"{duration * 1000:.2f}ms"
        response.headers["X-Timestamp"] = datetime.utcnow().isoformat()
        return response
