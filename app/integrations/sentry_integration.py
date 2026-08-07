"""Integration: sentry."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SentryIntegrationConfig:
    """Integration config."""
    name: str = 'sentry'
    api_key: str = ''
    api_secret: str = ''
    base_url: str = ''
    timeout: int = 30
    enabled: bool = True


@dataclass
class SentryIntegrationResult:
    """Integration result."""
    success: bool = False
    data: Any = None
    error: str | None = None
    status_code: int = 0


class SentryIntegration:
    """Integration."""

    def __init__(self, config: SentryIntegrationConfig | None = None):
        self.config = config or SentryIntegrationConfig()
        self._connected: bool = False
        self._last_sync: datetime | None = None
        self._rate_limit_remaining: int = 100

    async def connect(self) -> bool:
        """Connect."""
        if not self.config.api_key:
            logger.warning('No API key configured')
            return False
        self._connected = True
        return True

    async def disconnect(self) -> None:
        """Disconnect."""
        self._connected = False

    async def sync(self) -> SentryIntegrationResult:
        """Sync data."""
        if not self._connected:
            return SentryIntegrationResult(success=False, error='Not connected')
        self._last_sync = datetime.utcnow()
        return SentryIntegrationResult(success=True, data={}, status_code=200)

    async def push(self, data: Any) -> SentryIntegrationResult:
        """Push data."""
        if not self._connected:
            return SentryIntegrationResult(success=False, error='Not connected')
        return SentryIntegrationResult(success=True, data={}, status_code=200)

    async def pull(self, **params) -> SentryIntegrationResult:
        """Pull data."""
        if not self._connected:
            return SentryIntegrationResult(success=False, error='Not connected')
        return SentryIntegrationResult(success=True, data={}, status_code=200)

    def is_connected(self) -> bool:
        """Check connection."""
        return self._connected

    def get_last_sync(self) -> datetime | None:
        """Get last sync."""
        return self._last_sync
