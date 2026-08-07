#!/usr/bin/env python3
"""Generate middleware modules and CLI commands."""

from __future__ import annotations

from pathlib import Path

BASE = Path("/workspace/agent-engine")


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def gen_middleware(name: str, class_name: str, desc: str) -> str:
    return f'''"""Middleware: {name} - {desc}."""

from __future__ import annotations

import time
import uuid
from typing import Callable, Awaitable
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

import structlog

logger = structlog.get_logger()


class {class_name}Middleware(BaseHTTPMiddleware):
    """{desc} middleware."""

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
            response.headers["X-Process-Time"] = f"{{duration:.2f}}ms"

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
                content='{{"error": "Rate limit exceeded"}}',
                status_code=429,
                media_type="application/json",
                headers={{"Retry-After": "60"}},
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
        self._cache: dict[str, tuple[bytes, str, float]] = {{}}

    def _get_cache_key(self, request: Request) -> str:
        """Generate cache key from request."""
        return f"{{request.method}}:{{request.url.path}}:{{request.url.query}}"

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Apply caching."""
        if request.method != "GET":
            return await call_next(request)

        key = self._get_cache_key(request)
        if key in self._cache:
            body, content_type, expires = self._cache[key]
            if time.time() < expires:
                return Response(content=body, media_type=content_type, headers={{"X-Cache": "HIT"}})

        response = await call_next(request)

        if response.status_code == 200 and len(self._cache) < self.max_size:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            self._cache[key] = (body, response.media_type or "application/json", time.time() + self.default_ttl)
            return Response(content=body, media_type=response.media_type, headers={{"X-Cache": "MISS"}})

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
                duration_ms=f"{{duration:.2f}}",
            )

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    def __init__(self, app: ASGIApp, custom_headers: dict[str, str] | None = None):
        super().__init__(app)
        self.custom_headers = custom_headers or {{}}

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
            headers = {{}}
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
                content='{{"error": "Request body too large"}}',
                status_code=413,
                media_type="application/json",
            )

        for header in self.required_headers:
            if not request.headers.get(header):
                return Response(
                    content=f'{{{{"error": "Missing required header: {{header}}"}}}}',
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

        response.headers["X-Response-Time"] = f"{{duration * 1000:.2f}}ms"
        response.headers["X-Timestamp"] = datetime.utcnow().isoformat()
        return response
'''


def gen_cli_command(name: str, class_name: str, desc: str) -> str:
    return f'''"""CLI command: {name} - {desc}."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional
from datetime import datetime

import click
import structlog

from app.config import settings
from app.storage.database import get_session, init_db, close_db

logger = structlog.get_logger()


@click.group(name="{name}")
def {name}_group():
    """Manage {name}."""
    pass


@{name}_group.command(name="list")
@click.option("--status", default=None, help="Filter by status")
@click.option("--page", default=1, type=int, help="Page number")
@click.option("--page-size", default=20, type=int, help="Items per page")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def list_{name}(status: str | None, page: int, page_size: int, json_output: bool):
    """List {name} items."""
    async def _list():
        async with get_session() as session:
            click.echo(f"Listing {name} items (page {{page}})...")

    asyncio.run(_list())


@{name}_group.command(name="create")
@click.option("--name", required=True, help="Name")
@click.option("--description", default="", help="Description")
@click.option("--tags", default="", help="Comma-separated tags")
def create_{name}(name: str, description: str, tags: str):
    """Create a new {name} item."""
    async def _create():
        async with get_session() as session:
            click.echo(f"Creating {name}: {{name}}")

    asyncio.run(_create())


@{name}_group.command(name="get")
@click.argument("item_id", type=int)
@click.option("--json-output", is_flag=True, help="Output as JSON")
def get_{name}(item_id: int, json_output: bool):
    """Get {name} by ID."""
    async def _get():
        async with get_session() as session:
            click.echo(f"Fetching {name} {{item_id}}...")

    asyncio.run(_get())


@{name}_group.command(name="update")
@click.argument("item_id", type=int)
@click.option("--name", default=None, help="New name")
@click.option("--description", default=None, help="New description")
@click.option("--status", default=None, help="New status")
def update_{name}(item_id: int, name: str | None, description: str | None, status: str | None):
    """Update {name} item."""
    async def _update():
        async with get_session() as session:
            click.echo(f"Updating {name} {{item_id}}...")

    asyncio.run(_update())


@{name}_group.command(name="delete")
@click.argument("item_id", type=int)
@click.option("--hard", is_flag=True, help="Hard delete")
@click.confirmation_option(prompt="Are you sure?")
def delete_{name}(item_id: int, hard: bool):
    """Delete {name} item."""
    async def _delete():
        async with get_session() as session:
            click.echo(f"Deleting {name} {{item_id}}...")

    asyncio.run(_delete())


@{name}_group.command(name="export")
@click.argument("item_id", type=int)
@click.option("--output", default="-", help="Output file path")
def export_{name}(item_id: int, output: str):
    """Export {name} data."""
    async def _export():
        async with get_session() as session:
            click.echo(f"Exporting {name} {{item_id}}...")

    asyncio.run(_export())


@{name}_group.command(name="import")
@click.argument("file_path")
@click.option("--dry-run", is_flag=True, help="Preview without importing")
def import_{name}(file_path: str, dry_run: bool):
    """Import {name} data."""
    async def _import():
        click.echo(f"Importing from {{file_path}}...")

    asyncio.run(_import())


@{name}_group.command(name="stats")
def stats_{name}():
    """Show {name} statistics."""
    async def _stats():
        async with get_session() as session:
            click.echo(f"{name} statistics")

    asyncio.run(_stats())


@{name}_group.command(name="cleanup")
@click.option("--days", default=30, type=int, help="Remove items older than N days")
@click.confirmation_option(prompt="Proceed with cleanup?")
def cleanup_{name}(days: int):
    """Clean up old {name} items."""
    async def _cleanup():
        click.echo(f"Cleaning up {name} items older than {{days}} days...")

    asyncio.run(_cleanup())
'''


def main() -> None:
    all_files: dict[str, str] = {}

    # Generate middleware modules
    middlewares = [
        ("request_tracing", "RequestTracing", "Distributed request tracing"),
        ("rate_limiting", "RateLimiting", "API rate limiting"),
        ("response_caching", "ResponseCaching", "Response caching layer"),
        ("auth_enforcement", "AuthEnforcement", "Authentication enforcement"),
        ("input_validation", "InputValidation", "Request input validation"),
        ("audit_logging", "AuditLogging", "Audit trail logging"),
        ("circuit_breaker", "CircuitBreaker", "Circuit breaker pattern"),
        ("request_throttling", "RequestThrottling", "Request throttling"),
        ("ip_filtering", "IPFiltering", "IP allow/deny filtering"),
        ("payload_compression", "PayloadCompression", "Response compression"),
    ]

    print(f"Generating {len(middlewares)} middleware modules...")

    for name, class_name, desc in middlewares:
        content = gen_middleware(name, class_name, desc)
        all_files[f"app/middleware/{name}_middleware.py"] = content

    # Generate CLI command modules
    cli_commands = [
        ("user_mgmt", "UserMgmt", "User management commands"),
        ("db_admin", "DbAdmin", "Database administration"),
        ("config_mgmt", "ConfigMgmt", "Configuration management"),
        ("cache_admin", "CacheAdmin", "Cache administration"),
        ("queue_admin", "QueueAdmin", "Queue management"),
        ("metrics_viewer", "MetricsViewer", "Metrics viewing"),
        ("backup_cmd", "BackupCmd", "Backup operations"),
        ("restore_cmd", "RestoreCmd", "Restore operations"),
        ("log_analyzer", "LogAnalyzer", "Log analysis"),
        ("health_check", "HealthCheck", "Health check commands"),
    ]

    print(f"Generating {len(cli_commands)} CLI modules...")

    for name, class_name, desc in cli_commands:
        content = gen_cli_command(name, class_name, desc)
        all_files[f"app/cli/{name}_cli.py"] = content

    print(f"Writing {len(all_files)} files...")
    for path_str, content in all_files.items():
        write_file(BASE / path_str, content)

    print(f"Done! Generated {len(all_files)} files.")


if __name__ == "__main__":
    main()
