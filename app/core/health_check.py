"""Health Check — exposes system status for monitoring and alerting.

Provides:
- Comprehensive health status for all subsystems
- Middleware stack status
- Event bus health
- Metrics collector status
- Readiness and liveness probes
"""

from __future__ import annotations

import time
from typing import Any

import structlog

logger = structlog.get_logger()


class HealthChecker:
    """Checks health of all subsystems.

    Usage:
        checker = HealthChecker()
        status = await checker.check()
        ready = await checker.readiness()
        alive = await checker.liveness()
    """

    def __init__(self):
        self._start_time = time.time()

    async def check(self) -> dict[str, Any]:
        """Full health check of all subsystems."""
        checks = {}

        # Check middleware stack
        checks["middleware"] = await self._check_middleware()

        # Check event bus
        checks["event_bus"] = await self._check_event_bus()

        # Check metrics collector
        checks["metrics"] = await self._check_metrics()

        # Check sandbox
        checks["sandbox"] = await self._check_sandbox()

        # Overall status
        all_healthy = all(c.get("status") == "ok" for c in checks.values())

        return {
            "status": "ok" if all_healthy else "degraded",
            "timestamp": time.time(),
            "uptime_seconds": time.time() - self._start_time,
            "checks": checks,
        }

    async def readiness(self) -> bool:
        """Check if the system is ready to handle requests."""
        try:
            from app.core.middleware_config import get_middleware_config_manager
            manager = get_middleware_config_manager()
            manager.build_chain()
            return True
        except Exception:
            return False

    async def liveness(self) -> bool:
        """Check if the system is alive."""
        return True

    async def _check_middleware(self) -> dict[str, Any]:
        """Check middleware stack health."""
        try:
            from app.core.middleware_config import get_middleware_config_manager
            manager = get_middleware_config_manager()
            state = manager.get_state()
            return {
                "status": "ok",
                "middleware_count": len(state),
                "enabled_count": sum(1 for m in state if m.get("enabled")),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_event_bus(self) -> dict[str, Any]:
        """Check event bus health."""
        try:
            from app.core.event_bus import get_event_bus
            bus = get_event_bus()
            history = bus.get_history(limit=10)
            return {
                "status": "ok",
                "recent_events": len(history),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_metrics(self) -> dict[str, Any]:
        """Check metrics collector health."""
        try:
            from app.core.metrics_collector import get_metrics_collector
            collector = get_metrics_collector()
            snapshot = collector.snapshot()
            return {
                "status": "ok",
                "counter_count": len(snapshot.get("counters", {})),
                "histogram_count": len(snapshot.get("histograms", {})),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_sandbox(self) -> dict[str, Any]:
        """Check sandbox health."""
        try:
            from app.core.unified_sandbox import UnifiedSandbox
            UnifiedSandbox()
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Global health checker instance
_health_checker: HealthChecker | None = None


def get_health_checker() -> HealthChecker:
    """Get the global health checker."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker
