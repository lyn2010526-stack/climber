"""Fail-closed pairing gateway for external direct-message channels."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import StrEnum
from uuid import uuid4

DM_CHAT_CAPABILITY = "dm:chat"
DEFAULT_PAIRING_TTL_SECONDS = 600
DEFAULT_MAX_PENDING_PAIRINGS = 100


class PairingStatus(StrEnum):
    PENDING = "pending"
    PAIRED = "paired"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass(frozen=True, slots=True)
class ChannelPairing:
    id: str
    owner_user_id: str
    channel: str
    external_user_id: str
    conversation_id: str
    capability: str
    status: PairingStatus
    created_at: float
    expires_at: float | None
    approved_at: float | None = None
    revoked_at: float | None = None


@dataclass(frozen=True, slots=True)
class GatewayDecision:
    allowed: bool
    code: str
    pairing: ChannelPairing | None = None


class PairingError(Exception):
    """Pairing transition failure with a stable machine-readable code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


BindingKey = tuple[str, str, str, str]


class ChannelGateway:
    """Own in-process DM pairing state and enforce exact channel bindings."""

    def __init__(
        self,
        *,
        dm_enabled: bool = False,
        pairing_ttl_seconds: int = DEFAULT_PAIRING_TTL_SECONDS,
        max_pending_pairings: int = DEFAULT_MAX_PENDING_PAIRINGS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if pairing_ttl_seconds <= 0:
            raise ValueError("pairing_ttl_seconds must be positive")
        if max_pending_pairings <= 0:
            raise ValueError("max_pending_pairings must be positive")
        self.dm_enabled = dm_enabled
        self.pairing_ttl_seconds = pairing_ttl_seconds
        self.max_pending_pairings = max_pending_pairings
        self._clock = clock
        self._pairings: dict[BindingKey, ChannelPairing] = {}
        self._pairing_ids: dict[str, BindingKey] = {}
        self._lock = asyncio.Lock()

    async def authorize(
        self,
        *,
        channel: str,
        external_user_id: str,
        conversation_id: str,
        chat_type: str,
        owner_user_id: str = "default-user",
    ) -> GatewayDecision:
        """Authorize one DM binding, creating a pending request when absent."""
        if not self.dm_enabled:
            return GatewayDecision(False, "DM_DISABLED")
        if chat_type != "private":
            return GatewayDecision(False, "DIRECT_MESSAGE_REQUIRED")

        normalized = self._normalize_binding(
            owner_user_id,
            channel,
            external_user_id,
            conversation_id,
        )
        if normalized is None:
            return GatewayDecision(False, "INVALID_CHANNEL_CONTEXT")

        async with self._lock:
            now = self._clock()
            self._purge_expired(now)
            pairing = self._pairings.get(normalized)
            if pairing is None:
                pending_count = sum(
                    current.status is PairingStatus.PENDING
                    for current in self._pairings.values()
                )
                if pending_count >= self.max_pending_pairings:
                    return GatewayDecision(False, "PAIRING_CAPACITY_EXCEEDED")
                pairing = ChannelPairing(
                    id=str(uuid4()),
                    owner_user_id=normalized[0],
                    channel=normalized[1],
                    external_user_id=normalized[2],
                    conversation_id=normalized[3],
                    capability=DM_CHAT_CAPABILITY,
                    status=PairingStatus.PENDING,
                    created_at=now,
                    expires_at=now + self.pairing_ttl_seconds,
                )
                self._pairings[normalized] = pairing
                self._pairing_ids[pairing.id] = normalized
                return GatewayDecision(False, "PAIRING_PENDING", pairing)

            pairing = self._expire_if_needed(normalized, pairing, now)
            if pairing.status is PairingStatus.PAIRED:
                return GatewayDecision(True, "PAIRED", pairing)
            return GatewayDecision(False, f"PAIRING_{pairing.status.value.upper()}", pairing)

    async def list_pairings(
        self,
        *,
        owner_user_id: str,
        status: PairingStatus | None = None,
    ) -> list[ChannelPairing]:
        async with self._lock:
            now = self._clock()
            self._purge_expired(now)
            pairings: list[ChannelPairing] = []
            for key, current in list(self._pairings.items()):
                pairing = self._expire_if_needed(key, current, now)
                if pairing.owner_user_id != owner_user_id:
                    continue
                if status is None or pairing.status is status:
                    pairings.append(pairing)
            return sorted(pairings, key=lambda item: item.created_at, reverse=True)

    async def approve(self, pairing_id: str, *, owner_user_id: str) -> ChannelPairing:
        async with self._lock:
            key, pairing = self._owned_pairing(pairing_id, owner_user_id)
            now = self._clock()
            pairing = self._expire_if_needed(key, pairing, now)
            if pairing.status is PairingStatus.EXPIRED:
                self._remove_pairing(key, pairing)
                raise PairingError("PAIRING_EXPIRED")
            if pairing.status is not PairingStatus.PENDING:
                raise PairingError("PAIRING_STATE_CONFLICT")
            pairing = replace(
                pairing,
                status=PairingStatus.PAIRED,
                approved_at=now,
                expires_at=None,
            )
            self._pairings[key] = pairing
            return pairing

    async def revoke(self, pairing_id: str, *, owner_user_id: str) -> ChannelPairing:
        async with self._lock:
            key, pairing = self._owned_pairing(pairing_id, owner_user_id)
            if pairing.status is PairingStatus.REVOKED:
                return pairing
            now = self._clock()
            pairing = replace(
                pairing,
                status=PairingStatus.REVOKED,
                revoked_at=now,
            )
            self._pairings[key] = pairing
            return pairing

    def _owned_pairing(self, pairing_id: str, owner_user_id: str) -> tuple[BindingKey, ChannelPairing]:
        key = self._pairing_ids.get(pairing_id)
        pairing = self._pairings.get(key) if key else None
        if pairing is None or pairing.owner_user_id != owner_user_id:
            raise PairingError("PAIRING_NOT_FOUND")
        return key, pairing

    def _expire_if_needed(
        self,
        key: BindingKey,
        pairing: ChannelPairing,
        now: float,
    ) -> ChannelPairing:
        if (
            pairing.status is PairingStatus.PENDING
            and pairing.expires_at is not None
            and now >= pairing.expires_at
        ):
            pairing = replace(pairing, status=PairingStatus.EXPIRED)
            self._pairings[key] = pairing
        return pairing

    def _purge_expired(self, now: float) -> None:
        for key, pairing in list(self._pairings.items()):
            if pairing.status is PairingStatus.EXPIRED or (
                pairing.status is PairingStatus.PENDING
                and pairing.expires_at is not None
                and now >= pairing.expires_at
            ):
                self._remove_pairing(key, pairing)

    def _remove_pairing(self, key: BindingKey, pairing: ChannelPairing) -> None:
        self._pairings.pop(key, None)
        self._pairing_ids.pop(pairing.id, None)

    @staticmethod
    def _normalize_binding(
        owner_user_id: str,
        channel: str,
        external_user_id: str,
        conversation_id: str,
    ) -> BindingKey | None:
        values = (
            owner_user_id.strip(),
            channel.strip().lower(),
            external_user_id.strip(),
            conversation_id.strip(),
        )
        if any(not value for value in values):
            return None
        return values


_channel_gateway = ChannelGateway()


def get_channel_gateway() -> ChannelGateway:
    return _channel_gateway


def set_channel_gateway(gateway: ChannelGateway) -> None:
    global _channel_gateway
    _channel_gateway = gateway
