"""Middleware: metrics - HTTP middleware."""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = structlog.get_logger()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Metrics middleware."""

    def __init__(
        self,
        app: ASGIApp,
        excluded_paths: set[str] | None = None,
        enabled: bool = True,
    ):
        super().__init__(app)
        self.excluded_paths = excluded_paths or set()
        self.enabled = enabled
        self._request_count = 0
        self._error_count = 0

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request."""
        if not self.enabled:
            return await call_next(request)

        path = request.url.path
        if path in self.excluded_paths:
            return await call_next(request)

        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        self._request_count += 1

        request.state.request_id = request_id
        request.state.start_time = start_time

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            response.headers['X-Request-ID'] = request_id
            response.headers['X-Process-Time'] = f'{duration:.4f}'

            logger.info("Request completed",
                request_id=request_id,
                method=request.method,
                path=path,
                status_code=response.status_code,
                duration=duration,
            )

            return response

        except Exception as e:
            self._error_count += 1
            duration = time.time() - start_time
            logger.error("Request failed",
                request_id=request_id,
                method=request.method,
                path=path,
                error=str(e),
                duration=duration,
            )
            raise


class MetricsConfig:
    """Middleware configuration."""

    def __init__(
        self,
        enabled: bool = True,
        excluded_paths: set[str] | None = None,
        log_level: str = 'info',
    ):
        self.enabled = enabled
        self.excluded_paths = excluded_paths or {'/health', '/metrics', '/docs', '/openapi.json'}
        self.log_level = log_level


class MetricsStats:
    """Middleware statistics."""

    def __init__(self):
        self.total_requests = 0
        self.total_errors = 0
        self.avg_response_time = 0.0
        self.max_response_time = 0.0
        self.min_response_time = float('inf')
        self._response_times: list[float] = []

    def record(self, duration: float, is_error: bool = False) -> None:
        """Record request metrics."""
        self.total_requests += 1
        if is_error:
            self.total_errors += 1
        self._response_times.append(duration)
        self.max_response_time = max(self.max_response_time, duration)
        self.min_response_time = min(self.min_response_time, duration)
        self.avg_response_time = sum(self._response_times) / len(self._response_times)

    def get_summary(self) -> dict:
        """Get summary stats."""
        return {
            'total_requests': self.total_requests,
            'total_errors': self.total_errors,
            'error_rate': self.total_errors / max(self.total_requests, 1),
            'avg_response_time': self.avg_response_time,
            'max_response_time': self.max_response_time,
            'min_response_time': self.min_response_time if self.min_response_time != float('inf') else 0,
        }
