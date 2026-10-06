"""Provider contracts for local-first domestic ecosystem integrations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.core.security.domestic_adapter import QRToken, QRTokenStore


@dataclass(frozen=True, slots=True)
class ProviderStatus:
    provider: str
    enabled: bool
    mode: str
    reason: str


class QQBotProvider(Protocol):
    """Minimal contract a real QQBot adapter may implement later."""

    def status(self) -> ProviderStatus: ...

    def issue_binding_token(self) -> QRToken: ...

    def consume_binding_token(self, token: str) -> bool: ...


class DisabledQQBotProvider:
    """Safe default provider; it never contacts QQ or accepts credentials."""

    def __init__(self, token_store: QRTokenStore) -> None:
        self._token_store = token_store

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            "qqbot", False, "disabled", "external provider credentials are not configured"
        )

    def issue_binding_token(self) -> QRToken:
        raise RuntimeError("qqbot provider is disabled")

    def consume_binding_token(self, _token: str) -> bool:
        return False


class LocalQQBotProvider:
    """Deterministic local fake used by tests and offline development."""

    def __init__(self, token_store: QRTokenStore) -> None:
        self._token_store = token_store

    def status(self) -> ProviderStatus:
        return ProviderStatus("qqbot", True, "local", "local fake provider; no external calls")

    def issue_binding_token(self) -> QRToken:
        return self._token_store.issue()

    def consume_binding_token(self, token: str) -> bool:
        return self._token_store.consume(token)
