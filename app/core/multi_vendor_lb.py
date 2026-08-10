"""Multi-vendor API load balancer.

"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class VendorEndpoint:
    vendor: str
    api_key: str
    base_url: str
    weight: int = 1
    healthy: bool = True
    last_error: str | None = None
    last_error_time: float = 0.0
    total_calls: int = 0
    success_calls: int = 0
    total_latency_ms: float = 0.0
    cooldown_until: float = 0.0


class MultiVendorLoadBalancer:
    """Load balance API calls across multiple vendors.

    """

    def __init__(self):
        self._endpoints: list[VendorEndpoint] = []

    def register_endpoint(self, endpoint: VendorEndpoint) -> None:
        self._endpoints.append(endpoint)
        logger.info("vendor_registered", vendor=endpoint.vendor, base_url=endpoint.base_url)

    def get_endpoint(self) -> VendorEndpoint | None:
        now = time.monotonic()
        available = [ep for ep in self._endpoints if ep.healthy and now >= ep.cooldown_until]
        if not available:
            return self._endpoints[0] if self._endpoints else None
        weights = [ep.weight for ep in available]
        return random.choices(available, weights=weights, k=1)[0]  # noqa: S311 - weighted LB selection, non-crypto

    def record_success(self, vendor: str, latency_ms: float) -> None:
        for ep in self._endpoints:
            if ep.vendor == vendor:
                ep.total_calls += 1
                ep.success_calls += 1
                ep.total_latency_ms += latency_ms
                ep.healthy = True
                ep.last_error = None
                break

    def record_failure(self, vendor: str, error: str, cooldown_seconds: float = 60.0) -> None:
        now = time.monotonic()
        for ep in self._endpoints:
            if ep.vendor == vendor:
                ep.total_calls += 1
                ep.last_error = error
                ep.last_error_time = now
                ep.cooldown_until = now + cooldown_seconds
                if ep.total_calls > 0 and (ep.total_calls - ep.success_calls) / ep.total_calls > 0.5:
                    ep.healthy = False
                break

    def get_stats(self) -> dict[str, Any]:
        return {
            "endpoints": [
                {
                    "vendor": ep.vendor,
                    "healthy": ep.healthy,
                    "total_calls": ep.total_calls,
                    "success_rate": (ep.success_calls / ep.total_calls) if ep.total_calls > 0 else 0.0,
                    "avg_latency_ms": (ep.total_latency_ms / ep.total_calls) if ep.total_calls > 0 else 0.0,
                }
                for ep in self._endpoints
            ]
        }


load_balancer = MultiVendorLoadBalancer()
