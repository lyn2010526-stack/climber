"""Security middleware — rate limiting, security headers, input validation,
CSRF protection, and filesystem path isolation."""

from __future__ import annotations

import json
import re
import secrets
from collections.abc import Awaitable, Callable
from ipaddress import ip_address, ip_network
from urllib.parse import unquote

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.principal import get_context_principal
from app.core.security.fs_isolation import fs_isolation
from app.storage.usage import usage_tracker

logger = structlog.get_logger(__name__)

MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
MAX_JSON_DEPTH = 10

CSRF_TOKEN_HEADER = "X-CSRF-Token"
CSRF_TOKEN_COOKIE = "csrf_token"
CSRF_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
CSRF_EXEMPT_PATHS = frozenset(
    {
        "/health",
        "/health/logs",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/favicon.ico",
    }
)
# Authentication bootstrap: a caller has no token yet, so double-submit cannot
# be satisfied. These routes are reachable before a session exists and are
# protected by credential validation plus rate limiting instead.
CSRF_EXEMPT_PREFIXES = ("/api/v1/auth/login", "/api/v1/auth/refresh", "/api/v1/auth/register")
# Deployments that hand out API keys in query strings (documented in the
# README) cannot send a header, so they are exempt by design.
CSRF_EXEMPT_QUERY_KEYS = frozenset({"api_key", "access_token"})

# Request fields whose string values are treated as filesystem paths.
PATH_FIELD_NAMES = frozenset(
    {
        "path",
        "paths",
        "file",
        "file_path",
        "filepath",
        "filename",
        "file_name",
        "dir",
        "dirs",
        "directory",
        "base_dir",
        "base_path",
        "input_file",
        "input_path",
        "output_dir",
        "output_file",
        "output_path",
        "destination",
        "destination_path",
        "save_path",
        "source_path",
        "target_dir",
        "target_path",
        "upload_dir",
        "workspace",
        "workspace_dir",
        "workspace_path",
        "cwd",
    }
)
PATH_TRAVERSAL_PATTERN = re.compile(r"\.\.[\\/]|[~][\\/]|^(?:[a-zA-Z]:[\\/]|/)")


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
    """CSRF protection using double-submit cookie pattern.

    Enforcement scope, and why each exclusion exists:

    * Safe methods (``GET``/``HEAD``/``OPTIONS``/``TRACE``) only mint the cookie
      on the way out; they never mutate state, so no token is required.
    * ``CSRF_EXEMPT_PATHS`` are unauthenticated liveness/telemetry endpoints
      that are already safe methods or carry no user context.
    * ``CSRF_EXEMPT_PREFIXES`` are credential-bootstrap routes: the caller
      cannot hold a token before it authenticates.
    * Requests carrying an ``Authorization`` header are exempt. Those
      credentials are not ambient (the SPA keeps its bearer token in
      ``localStorage``), so a cross-site form post cannot forge them. This is
      what keeps non-browser API clients working.
    * ``CSRF_EXEMPT_QUERY_KEYS`` covers deployments that authenticate with a
      query-string API key, which cannot carry a header.
    """

    def __init__(
        self,
        app,
        excluded_paths: set[str] | None = None,
        enabled: bool = True,
        exempt_prefixes: tuple[str, ...] = CSRF_EXEMPT_PREFIXES,
    ):
        super().__init__(app)
        self.excluded_paths = set(excluded_paths) if excluded_paths is not None else set(CSRF_EXEMPT_PATHS)
        self.enabled = enabled
        self.exempt_prefixes = tuple(exempt_prefixes)

    def is_exempt(self, request: Request) -> tuple[bool, str]:
        """Return ``(exempt, reason)`` for this request."""
        path = request.url.path
        if path in self.excluded_paths:
            return True, "excluded path"
        if any(path.startswith(prefix) for prefix in self.exempt_prefixes):
            return True, "authentication bootstrap route"
        if request.headers.get("Authorization"):
            return True, "non-ambient Authorization credential"
        if CSRF_EXEMPT_QUERY_KEYS.intersection(request.query_params.keys()):
            return True, "query-string API credential"
        return False, ""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not self.enabled:
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

        exempt, reason = self.is_exempt(request)
        if exempt:
            logger.info("csrf_exempt", path=request.url.path, reason=reason)
            return await call_next(request)

        cookie_token = request.cookies.get(CSRF_TOKEN_COOKIE)
        header_token = request.headers.get(CSRF_TOKEN_HEADER)

        if not cookie_token or not header_token:
            return await self._reject(request, "CSRF token missing")

        if not secrets.compare_digest(cookie_token, header_token):
            return await self._reject(request, "CSRF token mismatch")

        return await call_next(request)

    async def _reject(self, request: Request, detail: str) -> Response:
        from app.core.observability.audit import audit_chain

        logger.warning("csrf_rejected", path=request.url.path, detail=detail)
        try:
            await audit_chain.log_security_decision(
                decision_type="csrf_check",
                allowed=False,
                reason=detail,
                subject=f"{request.method} {request.url.path}",
            )
        except Exception as exc:  # pragma: no cover - audit must not mask the refusal
            logger.warning("csrf_audit_failed", error=str(exc))
        return JSONResponse(
            status_code=403,
            content={"detail": detail, "type": "csrf_error"},
        )


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


def _looks_like_path(value: str) -> bool:
    """True when a string should be treated as a filesystem path."""
    return bool(PATH_TRAVERSAL_PATTERN.search(value))


def _iter_path_candidates(payload: object, key: str = "") -> list[tuple[str, str]]:
    """Collect ``(field_name, value)`` pairs whose field names denote paths."""
    found: list[tuple[str, str]] = []
    if isinstance(payload, dict):
        for child_key, child in payload.items():
            found.extend(_iter_path_candidates(child, str(child_key)))
    elif isinstance(payload, list):
        for child in payload:
            found.extend(_iter_path_candidates(child, key))
    elif isinstance(payload, str) and key.lower() in PATH_FIELD_NAMES and _looks_like_path(payload):
        found.append((key, payload))
    return found


class PathIsolationMiddleware(BaseHTTPMiddleware):
    """Refuse client-supplied filesystem paths that escape the isolation policy.

    Runs before the route handler, so a traversal payload is rejected instead of
    reaching a handler that would resolve it. Only fields whose *name* denotes a
    path and whose *value* looks like one are inspected, which keeps free-text
    payloads (prompts, workflow bodies, chat messages) out of scope.
    """

    SKIP_PATHS = {"/health", "/health/logs", "/metrics", "/docs", "/openapi.json"}

    def _is_skipped(self, request: Request) -> bool:
        return request.url.path in self.SKIP_PATHS

    def _refuse(self, field: str, value: str, reason: str) -> JSONResponse:
        detail = f"path field {field!r} rejected by filesystem isolation: {reason}"
        logger.warning("path_isolation_rejected", field=field, reason=reason)
        return JSONResponse(
            status_code=400,
            content={"detail": detail, "type": "path_isolation_error"},
        )

    def _check_value(self, field: str, value: str) -> str | None:
        """Return a refusal reason, or ``None`` when the path is acceptable."""
        if fs_isolation.PATH_TRAVERSAL_PATTERN.search(value):
            return f"path traversal detected in {value!r}"
        try:
            resolved = fs_isolation.sanitize_path(value)
        except ValueError as exc:
            return str(exc)
        ok, reason = fs_isolation.validate_path(resolved)
        if not ok:
            return reason
        return None

    async def _audit_refusal(
        self, request: Request, field: str, value: str, reason: str
    ) -> None:
        from app.core.observability.audit import audit_chain

        try:
            await audit_chain.log_security_decision(
                decision_type="path_isolation_check",
                allowed=False,
                reason=reason,
                subject=f"{request.method} {request.url.path} field={field} value={value[:200]}",
            )
        except Exception as exc:  # pragma: no cover - audit must not mask the refusal
            logger.warning("path_isolation_audit_failed", error=str(exc))

    async def dispatch(self, request: Request, call_next) -> Response:
        if self._is_skipped(request):
            return await call_next(request)

        # The raw request path is checked on every method: a handler that
        # resolves a path segment would otherwise be reachable via GET.
        raw_path_segments = unquote(request.url.path).split("/")
        if ".." in raw_path_segments:
            reason = f"path traversal detected in request path {request.url.path!r}"
            await self._audit_refusal(request, "url_path", request.url.path, reason)
            return self._refuse("url_path", request.url.path, reason)

        for field, value in _iter_path_candidates(dict(request.query_params)):
            reason = self._check_value(field, value)
            if reason:
                await self._audit_refusal(request, field, value, reason)
                return self._refuse(field, value, reason)

        if request.method in CSRF_SAFE_METHODS:
            return await call_next(request)

        if not request.headers.get("content-type", "").startswith("application/json"):
            return await call_next(request)

        raw_body = await request.body()
        if not raw_body:
            return await call_next(request)
        try:
            payload = json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return await call_next(request)

        for field, value in _iter_path_candidates(payload):
            reason = self._check_value(field, value)
            if reason:
                await self._audit_refusal(request, field, value, reason)
                return self._refuse(field, value, reason)

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

    def _rate_limit_key(self, request: Request) -> str:
        """Resolve the rate-limit key from the authenticated principal or client IP.

        Uses the same principal identity as the ``RateLimit`` dependency so both
        enforcement points count against one shared counter.
        """
        try:
            return get_context_principal().identity_key
        except RuntimeError:
            return self._get_client_ip(request)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS" or request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        key = self._rate_limit_key(request)

        allowed, reason = await usage_tracker.check_rate_limit(key)
        if not allowed:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={"detail": reason, "type": "rate_limit_exceeded"},
            )

        try:
            return await call_next(request)
        finally:
            await usage_tracker.record_request(key)
